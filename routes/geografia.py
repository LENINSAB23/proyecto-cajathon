from collections import defaultdict
from datetime import date

from flask import Blueprint, abort, current_app, render_template, request

from database.db import query_db
from routes.auth import login_required, role_required
from services.telegram_service import notify_telegram

geografia_bp = Blueprint("geografia", __name__, url_prefix="/concentracion")
MIN_CLIENTS_FOR_MAP_MARKER = 5


@geografia_bp.route("/")
@login_required
@role_required("Administrador", "Analista de créditos", "Personal de cobranza")
def index():
    start_date = request.args.get("desde", "").strip()
    end_date = request.args.get("hasta", "").strip()
    risk = request.args.get("riesgo", "").strip().upper()
    state = request.args.get("estado", "").strip().upper()
    valid_states = {"PENDIENTE", "EVALUADO", "APROBADO", "RECHAZADO", "OBSERVADO"}
    valid_risks = {"BAJO", "MEDIO", "ALTO"}
    try:
        if start_date:
            date.fromisoformat(start_date)
        if end_date:
            date.fromisoformat(end_date)
    except ValueError:
        abort(400, description="Use fechas válidas en formato AAAA-MM-DD.")
    if start_date and end_date and start_date > end_date:
        abort(400, description="La fecha inicial debe ser anterior o igual a la fecha final.")
    if risk and risk not in valid_risks:
        abort(400, description="El nivel de riesgo no es válido.")
    if state and state not in valid_states:
        abort(400, description="El estado de crédito no es válido.")
    clients = query_db("SELECT id, departamento, provincia, distrito, latitud, longitud, nivel_riesgo FROM clientes WHERE activo = TRUE")
    requests_by_client = defaultdict(list)
    application_filters = []
    application_params = []
    if start_date:
        application_filters.append("DATE(fecha_solicitud) >= DATE(?)")
        application_params.append(start_date)
    if end_date:
        application_filters.append("DATE(fecha_solicitud) <= DATE(?)")
        application_params.append(end_date)
    if state:
        application_filters.append("estado = ?")
        application_params.append(state)
    application_where = " WHERE " + " AND ".join(application_filters) if application_filters else ""
    applications = query_db(
        "SELECT id, cliente_id, monto_solicitado, estado, fecha_solicitud "
        "FROM solicitudes_credito" + application_where,
        application_params,
    )
    for application in applications:
        requests_by_client[application["cliente_id"]].append(application)

    payment_filters = []
    payment_params = []
    if start_date:
        payment_filters.append("DATE(p.fecha_vencimiento) >= DATE(?)")
        payment_params.append(start_date)
    if end_date:
        payment_filters.append("DATE(p.fecha_vencimiento) <= DATE(?)")
        payment_params.append(end_date)
    payment_where = " WHERE " + " AND ".join(payment_filters) if payment_filters else ""
    payments = query_db(
        """SELECT p.id, p.cliente_id, p.estado_pago, p.fecha_vencimiento,
                  CASE WHEN p.monto_cuota + p.penalidad - COALESCE(
                      (SELECT SUM(tp.monto) FROM transacciones_pago tp WHERE tp.cuota_id = p.id), 0
                  ) > 0 THEN p.monto_cuota + p.penalidad - COALESCE(
                      (SELECT SUM(tp.monto) FROM transacciones_pago tp WHERE tp.cuota_id = p.id), 0
                  ) ELSE 0 END AS saldo_cuota
           FROM pagos p""" + payment_where,
        payment_params,
    )
    payments_by_client = defaultdict(list)
    for payment in payments:
        payments_by_client[payment["cliente_id"]].append(payment)

    selected_client_ids = (
        set(requests_by_client)
        if start_date or end_date or state
        else {client["id"] for client in clients}
    )
    zones = defaultdict(lambda: {
        "clientes": {}, "creditos": 0, "monto_creditos": 0.0, "alto": 0,
        "morosos": 0, "exposicion_cartera": 0.0, "exposicion_vencida": 0.0,
        "latitudes": [], "longitudes": [],
    })
    for client in clients:
        if client["id"] not in selected_client_ids:
            continue
        if risk in valid_risks and client["nivel_riesgo"] != risk:
            continue
        location = tuple((client.get(key) or "").strip() for key in ("departamento", "provincia", "distrito"))
        if not any(location):
            location = ("Ubicación no registrada", "", "")
        zone = zones[location]
        zone["clientes"][client["id"]] = client
        zone["alto"] += client["nivel_riesgo"] == "ALTO"
        for application in requests_by_client[client["id"]]:
            zone["creditos"] += 1
            zone["monto_creditos"] += float(application["monto_solicitado"] or 0)
        client_payments = payments_by_client[client["id"]]
        zone["exposicion_cartera"] += sum(
            float(payment["saldo_cuota"] or 0)
            for payment in client_payments if payment["estado_pago"] != "PAGADO"
        )
        client_overdue = [
            payment for payment in client_payments
            if payment["estado_pago"] in ("EN_MORA", "VENCIDO")
            or (
                payment["estado_pago"] != "PAGADO"
                and str(payment["fecha_vencimiento"])[:10] < date.today().isoformat()
            )
        ]
        if client_overdue:
            zone["morosos"] += 1
            zone["exposicion_vencida"] += sum(
                float(item["saldo_cuota"] or 0)
                for item in client_overdue
            )
        if client.get("latitud") is not None and client.get("longitud") is not None:
            zone["latitudes"].append(float(client["latitud"]))
            zone["longitudes"].append(float(client["longitud"]))

    results = []
    suppressed = {
        "clientes": 0, "creditos": 0, "monto_creditos": 0.0, "clientes_riesgo_alto": 0,
        "morosos": 0, "exposicion_cartera": 0.0, "exposicion_vencida": 0.0,
    }
    for location, zone in zones.items():
        count = len(zone["clientes"])
        if count < MIN_CLIENTS_FOR_MAP_MARKER:
            for key in suppressed:
                source_key = {"clientes": None, "clientes_riesgo_alto": "alto"}.get(key, key)
                suppressed[key] += len(zone["clientes"]) if source_key is None else zone[source_key]
            continue
        ratio = zone["morosos"] / count if count else 0
        risk_level = (
            "ALTO" if ratio * 100 >= current_app.config["GEO_MORA_HIGH"]
            else "MEDIO" if ratio * 100 >= current_app.config["GEO_MORA_MEDIUM"]
            else "BAJO"
        )
        mapped = count >= MIN_CLIENTS_FOR_MAP_MARKER and len(zone["latitudes"]) >= MIN_CLIENTS_FOR_MAP_MARKER
        results.append({
            "departamento": location[0], "provincia": location[1], "distrito": location[2],
            "clientes": count, "creditos": zone["creditos"], "monto_creditos": round(zone["monto_creditos"], 2),
            "clientes_riesgo_alto": zone["alto"], "morosos": zone["morosos"],
            "exposicion_cartera": round(zone["exposicion_cartera"], 2),
            "exposicion_vencida": round(zone["exposicion_vencida"], 2),
            "porcentaje_mora": round(ratio * 100, 1), "riesgo_zona": risk_level,
            "latitud": sum(zone["latitudes"]) / len(zone["latitudes"]) if mapped else None,
            "longitud": sum(zone["longitudes"]) / len(zone["longitudes"]) if mapped else None,
            "ubicacion_suprimida": False,
        })
    if suppressed["clientes"]:
        count = suppressed["clientes"]
        ratio = suppressed["morosos"] / count
        results.append({
            "departamento": "Otras ubicaciones (<5 clientes)", "provincia": "", "distrito": "",
            **suppressed, "porcentaje_mora": round(ratio * 100, 1),
            "riesgo_zona": (
                "ALTO" if ratio * 100 >= current_app.config["GEO_MORA_HIGH"]
                else "MEDIO" if ratio * 100 >= current_app.config["GEO_MORA_MEDIUM"]
                else "BAJO"
            ),
            "latitud": None, "longitud": None, "ubicacion_suprimida": True,
        })
    results.sort(key=lambda item: (item["exposicion_vencida"], item["clientes"]), reverse=True)

    high_zones = [
        zone for zone in results
        if zone["riesgo_zona"] == "ALTO" and zone["morosos"] and not zone["ubicacion_suprimida"]
    ]
    for zone in high_zones:
        notify_telegram(
            f"high-risk-zone:{zone['departamento']}:{zone['provincia']}:{zone['distrito']}:{zone['clientes']}:{zone['morosos']}",
            f"Alerta de concentración de morosidad: {zone['departamento']} / {zone['provincia']} / {zone['distrito'] or 'Provincia'}. "
            f"{zone['morosos']} de {zone['clientes']} clientes con mora ({zone['porcentaje_mora']}%).",
        )

    return render_template(
        "concentracion.html", zonas=results,
        mapped_zones=[zone for zone in results if zone["latitud"] is not None],
        start_date=start_date, end_date=end_date, risk=risk, state=state,
        map_min_clients=MIN_CLIENTS_FOR_MAP_MARKER,
        medium_threshold=current_app.config["GEO_MORA_MEDIUM"],
        high_threshold=current_app.config["GEO_MORA_HIGH"],
    )
