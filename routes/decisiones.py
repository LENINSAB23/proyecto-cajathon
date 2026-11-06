import json
from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, session, url_for

from database.db import query_db
from routes.auth import login_required, role_required
from services.financial_health import record_decision
from services.report_service import generar_excel_reporte, generar_pdf_reporte

decisiones_bp = Blueprint("decisiones", __name__, url_prefix="/decisiones")


def _filtered_history():
    clauses = ["1 = 1"]
    params = []
    for key, operator in (("desde", ">="), ("hasta", "<=")):
        value = request.args.get(key, "").strip()
        if value:
            try:
                date.fromisoformat(value)
            except ValueError:
                abort(400, description="Use fechas válidas en formato AAAA-MM-DD.")
            clauses.append(f"DATE(h.created_at) {operator} DATE(?)")
            params.append(value)
    for key, column in (("usuario", "h.actor_id"), ("cliente", "h.cliente_id"), ("estado", "h.estado_decision")):
        value = request.args.get(key, "").strip()
        if value:
            if key == "estado" and value not in {
                "EVALUADO", "APROBADO", "RECHAZADO", "OBSERVADO", "DESEMBOLSADO"
            }:
                abort(400, description="El estado de decisión no es válido.")
            clauses.append(f"{column} = ?")
            params.append(value)
    if session.get("user_role") == "Analista de créditos":
        clauses.append("h.actor_id = ?")
        params.append(session["user_id"])
    sql = f"""
        SELECT h.id, h.solicitud_id, h.cliente_id, h.actor_id, h.actor_nombre,
               h.tipo_evento, h.estado_decision, h.nivel_riesgo, h.score_riesgo,
               h.observaciones, h.snapshot_json, h.created_at,
               c.codigo_cliente, c.nombres, c.apellidos,
               s.numero_solicitud
        FROM historial_decisiones h
        JOIN clientes c ON c.id = h.cliente_id
        JOIN solicitudes_credito s ON s.id = h.solicitud_id
        WHERE {" AND ".join(clauses)}
        ORDER BY h.created_at DESC
    """
    return query_db(sql, params)


@decisiones_bp.route("/")
@login_required
@role_required("Administrador", "Analista de créditos")
def index():
    history = _filtered_history()
    users = query_db("SELECT DISTINCT actor_id, actor_nombre FROM historial_decisiones ORDER BY actor_nombre")
    clients = query_db("SELECT DISTINCT c.id, c.codigo_cliente, c.nombres, c.apellidos FROM clientes c JOIN historial_decisiones h ON h.cliente_id = c.id ORDER BY c.apellidos")
    return render_template(
        "decisiones.html", history=history, users=users, clients=clients,
        filters={key: request.args.get(key, "") for key in ("desde", "hasta", "usuario", "cliente", "estado")},
    )


@decisiones_bp.route("/<decision_id>")
@login_required
@role_required("Administrador", "Analista de créditos")
def detail(decision_id):
    row = query_db("SELECT * FROM historial_decisiones WHERE id = ?", (decision_id,), one=True)
    if not row:
        abort(404)
    if session.get("user_role") == "Analista de créditos" and row["actor_id"] != session["user_id"]:
        abort(403)
    row["snapshot"] = json.loads(row["snapshot_json"])
    return render_template("decision_detalle.html", decision=row)


@decisiones_bp.route("/solicitud/<solicitud_id>/observaciones", methods=["POST"])
@login_required
@role_required("Administrador")
def add_observation(solicitud_id):
    observation = request.form.get("observaciones", "").strip()
    if not observation or len(observation) > 4000:
        flash("La observación es obligatoria y no debe exceder 4000 caracteres.", "danger")
        return redirect(url_for("decisiones.index"))
    application = query_db("SELECT * FROM solicitudes_credito WHERE id = ?", (solicitud_id,), one=True)
    if not application:
        abort(404)
    evaluation = query_db("SELECT * FROM evaluaciones_riesgo WHERE solicitud_id = ?", (solicitud_id,), one=True)
    record_decision(
        "OBSERVACION_ADMIN", application, evaluation, application["estado"],
        observation, session.get("user_id"), session.get("user_name", "Administrador"),
    )
    flash("Observación agregada al historial inmutable.", "success")
    return redirect(url_for("decisiones.index"))


@decisiones_bp.route("/exportar/<format_name>")
@login_required
@role_required("Administrador", "Analista de créditos")
def export(format_name):
    if format_name not in ("excel", "pdf"):
        abort(404)
    rows = _filtered_history()
    report_rows = []
    for row in rows:
        snapshot = json.loads(row["snapshot_json"])
        evaluation = snapshot.get("evaluacion") or {}
        report_rows.append({
            "Fecha": row["created_at"],
            "Solicitud": row["numero_solicitud"],
            "Cliente": f"{row['codigo_cliente']} · {row['nombres']} {row['apellidos']}",
            "Evento": row["tipo_evento"],
            "Estado": row["estado_decision"] or "",
            "Nivel de riesgo": row["nivel_riesgo"] or "",
            "Score": row["score_riesgo"] if row["score_riesgo"] is not None else "",
            "Usuario": row["actor_nombre"],
            "Recomendaciones IA": evaluation.get("recomendaciones", ""),
            "Observaciones": row["observaciones"] or "",
        })
    report_title = "Historial de decisiones crediticias"
    stream = (
        generar_excel_reporte(report_title, report_rows)
        if format_name == "excel"
        else generar_pdf_reporte(report_title, report_rows, {"Registros": str(len(rows)), "Historial": "Solo lectura"})
    )
    if format_name == "excel":
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        extension = "xlsx"
    else:
        mime, extension = "application/pdf", "pdf"
    return send_file(stream, mimetype=mime, as_attachment=True, download_name=f"decisiones_crediticias.{extension}")
