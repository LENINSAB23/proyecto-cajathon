from collections import defaultdict
from datetime import date

from database.db import query_db


def _number(value):
    return float(value or 0)


def calculate_financial_health(warning_threshold, critical_threshold):
    """Calculate portfolio indicators from recorded credit and payment data."""
    approved = query_db(
        """SELECT id, cliente_id, monto_desembolsado, fecha_desembolso
           FROM solicitudes_credito
           WHERE monto_desembolsado > 0 AND fecha_desembolso IS NOT NULL"""
    )
    scheduled = query_db("""
        SELECT p.id, p.cliente_id, p.fecha_vencimiento,
               p.estado_pago, c.departamento, c.provincia, c.distrito, c.nivel_riesgo,
               CASE WHEN p.monto_cuota + p.penalidad - COALESCE(
                   (SELECT SUM(tp.monto) FROM transacciones_pago tp WHERE tp.cuota_id = p.id), 0
               ) > 0 THEN p.monto_cuota + p.penalidad - COALESCE(
                   (SELECT SUM(tp.monto) FROM transacciones_pago tp WHERE tp.cuota_id = p.id), 0
               ) ELSE 0 END AS saldo_cuota
        FROM pagos p JOIN clientes c ON c.id = p.cliente_id
    """)
    recoveries = query_db("SELECT monto, fecha_pago FROM transacciones_pago")
    clients = query_db("SELECT id, nivel_riesgo FROM clientes WHERE activo = TRUE")

    placed = sum(_number(item["monto_desembolsado"]) for item in approved)
    unpaid = [
        row for row in scheduled
        if row["estado_pago"] != "PAGADO"
    ]
    overdue = [
        row for row in unpaid
        if str(row["fecha_vencimiento"])[:10] < date.today().isoformat()
    ]
    overdue_amount = sum(_number(row["saldo_cuota"]) for row in overdue)
    outstanding_amount = sum(_number(row["saldo_cuota"]) for row in unpaid)
    recovery_amount = sum(_number(item["monto"]) for item in recoveries)
    delinquency_rate = overdue_amount / outstanding_amount * 100 if outstanding_amount else 0.0
    high_risk_count = sum(1 for row in clients if row["nivel_riesgo"] == "ALTO")

    if not scheduled or outstanding_amount == 0:
        health_status = "SIN DATOS"
    elif delinquency_rate >= critical_threshold:
        health_status = "ROJO"
    elif delinquency_rate >= warning_threshold:
        health_status = "AMARILLO"
    else:
        health_status = "VERDE"

    department_exposure = defaultdict(float)
    for row in scheduled:
        if row["estado_pago"] != "PAGADO":
            location = row["departamento"] or "Ubicación no registrada"
            department_exposure[location] += _number(row["saldo_cuota"])
    total_exposure = sum(department_exposure.values())
    concentration_hhi = (
        sum((amount / total_exposure * 100) ** 2 for amount in department_exposure.values())
        if total_exposure else None
    )

    monthly = defaultdict(lambda: {"colocado": 0.0, "recuperado": 0.0})
    for row in approved:
        month = str(row["fecha_desembolso"])[:7]
        monthly[month]["colocado"] += _number(row["monto_desembolsado"])
    for row in recoveries:
        month = str(row["fecha_pago"])[:7]
        monthly[month]["recuperado"] += _number(row["monto"])
    current_month = date.today().year * 12 + date.today().month - 1
    month_indices = [current_month - offset for offset in range(11, -1, -1)]
    months = [f"{index // 12:04d}-{index % 12 + 1:02d}" for index in month_indices]
    comparison = {}
    for metric in ("colocado", "recuperado"):
        previous_six = sum(monthly[month][metric] for month in months[:6])
        latest_six = sum(monthly[month][metric] for month in months[6:])
        comparison[metric] = {
            "periodo_anterior_6_meses": round(previous_six, 2),
            "periodo_reciente_6_meses": round(latest_six, 2),
            "variacion_porcentual": (
                round((latest_six - previous_six) / previous_six * 100, 2)
                if previous_six else None
            ),
        }
    risk_distribution = {
        level: sum(1 for row in clients if row["nivel_riesgo"] == level)
        for level in ("BAJO", "MEDIO", "ALTO")
    }

    return {
        "total_creditos_otorgados": len(approved),
        "dinero_colocado": placed if approved else None,
        "cartera_vigente": outstanding_amount,
        "cartera_vencida": overdue_amount,
        "porcentaje_morosidad": round(delinquency_rate, 2),
        "clientes_activos": len(clients),
        "clientes_riesgo_alto": high_risk_count,
        "distribucion_riesgos": risk_distribution,
        "dinero_recuperado": recovery_amount,
        "perdida_crediticia_esperada": None,
        "concentracion_cartera_hhi": round(concentration_hhi, 2) if concentration_hhi is not None else None,
        "liquidez": None,
        "estado_salud": health_status,
        "threshold_warning": warning_threshold,
        "threshold_critical": critical_threshold,
        "labels": months,
        "colocado_mensual": [round(monthly[m]["colocado"], 2) for m in months],
        "recuperado_mensual": [round(monthly[m]["recuperado"], 2) for m in months],
        "comparacion_periodos": comparison,
        "series_morosidad_disponible": False,
    }


def record_decision(event_type, solicitud, evaluation, decision, observation, actor_id, actor_name):
    import json
    from database.db import new_id, execute_db

    client = query_db("SELECT * FROM clientes WHERE id = ?", (solicitud["cliente_id"],), one=True)
    request_snapshot = dict(solicitud)
    for private_field in ("nombres", "apellidos", "dni", "edad", "telefono", "email"):
        request_snapshot.pop(private_field, None)
    snapshot = {
        "solicitud": request_snapshot,
        "cliente": {
            key: client.get(key) for key in (
                "codigo_cliente", "ingresos_mensuales", "gastos_mensuales",
                "deudas_actuales", "departamento", "provincia", "distrito",
            )
        } if client else {},
        "evaluacion": dict(evaluation) if evaluation else None,
        "decision": decision,
        "observaciones": observation,
    }
    execute_db("""
        INSERT INTO historial_decisiones (
            id, solicitud_id, cliente_id, actor_id, actor_nombre, tipo_evento,
            estado_decision, nivel_riesgo, score_riesgo, observaciones, snapshot_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        new_id("dec"), solicitud["id"], solicitud["cliente_id"], actor_id,
        actor_name, event_type, decision,
        evaluation.get("nivel_riesgo") if evaluation else None,
        evaluation.get("score_riesgo") if evaluation else None,
        observation, json.dumps(snapshot, default=str, ensure_ascii=False),
    ))
