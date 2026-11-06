import json
import math
from datetime import date, datetime
from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, session, url_for

from database.db import execute_db, query_db
from routes.auth import login_required, role_required
from services.financial_health import calculate_financial_health, record_decision
from services.report_service import generar_excel_reporte, generar_pdf_reporte
from services.telegram_service import notify_telegram

salud_bp = Blueprint("salud", __name__, url_prefix="/salud-financiera")


def _data():
    data = calculate_financial_health(
        current_app.config["HEALTH_MORA_WARNING"],
        current_app.config["HEALTH_MORA_CRITICAL"],
    )
    if data["estado_salud"] == "ROJO":
        notify_telegram(
            f"financial-health-critical:{datetime.now().strftime('%Y-%m')}",
            f"CAJA INTELIGENTE: el indicador de salud financiera está CRÍTICO. "
            f"Morosidad calculada: {data['porcentaje_morosidad']}%.",
        )
    return data


@salud_bp.route("/")
@login_required
@role_required("Administrador")
def index():
    pending_disbursements = query_db("""
        SELECT s.id, s.numero_solicitud, s.monto_solicitado, c.codigo_cliente, c.nombres, c.apellidos
        FROM solicitudes_credito s JOIN clientes c ON c.id = s.cliente_id
        WHERE s.estado = 'APROBADO' AND s.monto_desembolsado IS NULL
        ORDER BY s.fecha_solicitud DESC
    """)
    return render_template(
        "salud_financiera.html", health=_data(),
        pending_disbursements=pending_disbursements, today=date.today().isoformat(),
    )


@salud_bp.route("/registrar-desembolso/<solicitud_id>", methods=["POST"])
@login_required
@role_required("Administrador")
def register_disbursement(solicitud_id):
    try:
        amount = float(request.form.get("monto_desembolsado", "0"))
        disbursed_on = date.fromisoformat(request.form.get("fecha_desembolso", ""))
        application = query_db(
            """SELECT s.*, c.codigo_cliente FROM solicitudes_credito s
               JOIN clientes c ON c.id = s.cliente_id WHERE s.id = ?""",
            (solicitud_id,), one=True
        )
        if (
            not application or application["estado"] != "APROBADO"
            or application.get("monto_desembolsado") is not None
            or not math.isfinite(amount) or amount <= 0 or amount > float(application["monto_solicitado"])
            or disbursed_on > date.today()
        ):
            flash("Verifique que la solicitud esté aprobada, no desembolsada, y que el importe y fecha sean válidos.", "danger")
            return redirect(url_for("salud.index"))
        _, updated_count = execute_db("""
            UPDATE solicitudes_credito
            SET monto_desembolsado = ?, fecha_desembolso = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND estado = 'APROBADO' AND monto_desembolsado IS NULL
        """, (amount, disbursed_on.isoformat(), solicitud_id))
        if updated_count != 1:
            flash("No se pudo registrar el desembolso; vuelva a cargar el registro.", "warning")
            return redirect(url_for("salud.index"))
        application = query_db("SELECT * FROM solicitudes_credito WHERE id = ?", (solicitud_id,), one=True)
        record_decision(
            "DESEMBOLSO", application, None, "DESEMBOLSADO",
            f"Desembolso real registrado por S/ {amount:.2f} con fecha {disbursed_on.isoformat()}.",
            session.get("user_id"), session.get("user_name", "Administrador"),
        )
        flash("Desembolso registrado en el historial auditable.", "success")
    except (TypeError, ValueError):
        flash("El importe o la fecha del desembolso no son válidos.", "danger")
    return redirect(url_for("salud.index"))


@salud_bp.route("/exportar/<format_name>")
@login_required
@role_required("Administrador")
def export(format_name):
    if format_name not in ("excel", "pdf"):
        return "Formato no encontrado", 404
    data = _data()
    rows = [{
        "Indicador": key.replace("_", " ").title(),
        "Valor": "No disponible" if value is None else (
            json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
        ),
    } for key, value in data.items() if key not in {"labels", "colocado_mensual", "recuperado_mensual"}]
    title = "Indicadores de salud financiera"
    stream = generar_excel_reporte(title, rows) if format_name == "excel" else generar_pdf_reporte(title, rows, {})
    if format_name == "excel":
        mime, extension = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"
    else:
        mime, extension = "application/pdf", "pdf"
    return send_file(stream, mimetype=mime, as_attachment=True, download_name=f"salud_financiera.{extension}")


@salud_bp.route("/api")
@login_required
@role_required("Administrador")
def api():
    return _data()
