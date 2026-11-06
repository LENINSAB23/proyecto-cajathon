from datetime import date, timedelta
import math

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from database.db import execute_db, new_id, query_db
from routes.auth import login_required, role_required
from services.telegram_service import notify_telegram

promesas_bp = Blueprint("promesas", __name__, url_prefix="/promesas")


def _refresh_statuses():
    promises = query_db("""
        SELECT p.*, COALESCE(SUM(t.monto), 0) AS pagado
        FROM promesas_pago p
        LEFT JOIN transacciones_pago t ON t.promesa_id = p.id
        WHERE p.estado IN ('PENDIENTE', 'VENCIDA', 'INCUMPLIDA')
        GROUP BY p.id
    """)
    today = date.today()
    for promise in promises:
        amount_due = float(promise["monto_comprometido"])
        amount_paid = float(promise["pagado"] or 0)
        promised_date = promise["fecha_prometida"]
        if not isinstance(promised_date, date):
            promised_date = date.fromisoformat(str(promised_date)[:10])
        next_status = "CUMPLIDA" if amount_paid >= amount_due else (
            "INCUMPLIDA" if promised_date < today else
            "VENCIDA" if promised_date == today else "PENDIENTE"
        )
        if next_status != promise["estado"]:
            execute_db(
                "UPDATE promesas_pago SET estado = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (next_status, promise["id"]),
            )
        if next_status == "INCUMPLIDA" and not promise["alerta_incumplimiento_enviada"]:
            _create_alert(promise, "Promesa de pago incumplida", "ALTA")
            execute_db("UPDATE promesas_pago SET alerta_incumplimiento_enviada = TRUE WHERE id = ?", (promise["id"],))
            notify_telegram(
                f"promise-missed:{promise['id']}",
                f"Promesa de pago incumplida: cliente {promise['codigo_cliente']}, "
                f"compromiso S/ {amount_due:.2f} para {promised_date.isoformat()}.",
            )
        elif next_status in ("PENDIENTE", "VENCIDA") and promised_date <= today + timedelta(days=3) and not promise["alerta_proxima_enviada"]:
            _create_alert(promise, "Próximo vencimiento de promesa de pago", "MEDIA")
            execute_db("UPDATE promesas_pago SET alerta_proxima_enviada = TRUE WHERE id = ?", (promise["id"],))
            notify_telegram(
                f"promise-due-soon:{promise['id']}",
                f"Promesa de pago próxima a vencer: cliente {promise['codigo_cliente']}, "
                f"compromiso S/ {amount_due:.2f} para {promised_date.isoformat()}.",
            )


def _create_alert(promise, alert_type, severity):
    execute_db("""
        INSERT INTO alertas (id, cliente_id, tipo_alerta, severidad, mensaje, accion_recomendada)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        new_id("alt"), promise["cliente_id"], alert_type, severity,
        f"{alert_type}: compromiso S/ {float(promise['monto_comprometido']):.2f}, fecha {promise['fecha_prometida']}.",
        "Contactar al cliente y registrar el resultado del seguimiento.",
    ))


@promesas_bp.route("/")
@login_required
@role_required("Administrador", "Personal de cobranza")
def index():
    _refresh_statuses()
    promises = query_db("""
        SELECT p.*, c.codigo_cliente, c.nombres, c.apellidos,
               COALESCE(SUM(t.monto), 0) AS monto_pagado
        FROM promesas_pago p
        JOIN clientes c ON c.id = p.cliente_id
        LEFT JOIN transacciones_pago t ON t.promesa_id = p.id
        GROUP BY p.id, c.id
        ORDER BY p.fecha_prometida DESC, p.created_at DESC
    """)
    clients = query_db("""
        SELECT DISTINCT c.id, c.codigo_cliente, c.nombres, c.apellidos
        FROM clientes c JOIN pagos p ON p.cliente_id = c.id
        WHERE p.estado_pago != 'PAGADO'
        ORDER BY c.apellidos, c.nombres
    """)
    users = query_db("""
        SELECT id, nombre FROM usuarios
        WHERE activo = TRUE AND rol IN ('Administrador', 'Personal de cobranza')
        ORDER BY nombre
    """)
    counts = {state: sum(item["estado"] == state for item in promises) for state in
              ("PENDIENTE", "VENCIDA", "CUMPLIDA", "INCUMPLIDA")}
    closed = counts["CUMPLIDA"] + counts["INCUMPLIDA"]
    compliance = round(counts["CUMPLIDA"] / closed * 100, 1) if closed else None
    return render_template(
        "promesas.html", promises=promises, clients=clients, users=users,
        counts=counts, compliance=compliance, today=date.today().isoformat(),
    )


@promesas_bp.route("/crear", methods=["POST"])
@login_required
@role_required("Administrador", "Personal de cobranza")
def create():
    try:
        client_id = request.form.get("cliente_id", "").strip()
        amount = float(request.form.get("monto_comprometido", "0"))
        due_date = date.fromisoformat(request.form.get("fecha_prometida", ""))
        observation = request.form.get("observaciones", "").strip()
        responsible_id = request.form.get("responsable_id", "").strip() or session["user_id"]
        client = query_db("SELECT id FROM clientes WHERE id = ? AND activo = TRUE", (client_id,), one=True)
        responsible = query_db(
            "SELECT id, nombre FROM usuarios WHERE id = ? AND activo = TRUE AND rol IN ('Administrador', 'Personal de cobranza')",
            (responsible_id,), one=True
        )
        if (
            not client or not responsible or not math.isfinite(amount) or amount <= 0
            or due_date < date.today() or len(observation) > 1000
        ):
            flash("Revise cliente, responsable, monto positivo y fecha futura o de hoy.", "danger")
            return redirect(url_for("promesas.index"))
        execute_db("""
            INSERT INTO promesas_pago (
                id, cliente_id, monto_comprometido, fecha_prometida, observaciones,
                responsable_id, responsable_nombre, registrado_por, estado
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDIENTE')
        """, (
            new_id("prm"), client_id, amount, due_date.isoformat(), observation,
            responsible["id"], responsible["nombre"], session["user_id"],
        ))
        flash("Promesa de pago registrada.", "success")
    except (TypeError, ValueError):
        flash("El monto o la fecha de la promesa no son válidos.", "danger")
    return redirect(url_for("promesas.index"))


@promesas_bp.route("/cliente/<cliente_id>")
@login_required
@role_required("Administrador", "Personal de cobranza")
def client_history(cliente_id):
    rows = query_db("""
        SELECT p.*, COALESCE(SUM(t.monto), 0) AS monto_pagado
        FROM promesas_pago p
        LEFT JOIN transacciones_pago t ON t.promesa_id = p.id
        WHERE p.cliente_id = ?
        GROUP BY p.id ORDER BY p.created_at DESC
    """, (cliente_id,))
    return render_template("promesas_historial.html", promises=rows, cliente_id=cliente_id)
