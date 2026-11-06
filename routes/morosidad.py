from datetime import date, datetime
import math
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from routes.auth import login_required, role_required
from database.db import new_id, query_db, execute_db, execute_transaction
from services.credit_scoring import clasificar_dias_mora_sbs

morosidad_bp = Blueprint('morosidad', __name__, url_prefix='/morosidad')

@morosidad_bp.route('/')
@login_required
@role_required('Administrador', 'Personal de cobranza')
def index():
    from routes.promesas import _refresh_statuses
    _refresh_statuses()

    estado_filtro = request.args.get('estado', '').strip()
    nivel_filtro = request.args.get('clasificacion', '').strip()

    sql = """
        SELECT p.*,
               CASE WHEN p.monto_cuota + p.penalidad - COALESCE(
                   (SELECT SUM(tp.monto) FROM transacciones_pago tp WHERE tp.cuota_id = p.id), 0
               ) > 0 THEN p.monto_cuota + p.penalidad - COALESCE(
                   (SELECT SUM(tp.monto) FROM transacciones_pago tp WHERE tp.cuota_id = p.id), 0
               ) ELSE 0 END AS saldo_pendiente,
               c.nombres, c.apellidos, c.dni, c.codigo_cliente, c.telefono, c.ocupacion,
               s.numero_solicitud, s.tipo_credito
        FROM pagos p
        JOIN clientes c ON p.cliente_id = c.id
        JOIN solicitudes_credito s ON p.solicitud_id = s.id
        WHERE 1=1
    """
    params = []

    if estado_filtro:
        sql += " AND p.estado_pago = ?"
        params.append(estado_filtro)

    if nivel_filtro:
        sql += " AND p.clasificacion_sbs LIKE ?"
        params.append(f"%{nivel_filtro}%")

    sql += " ORDER BY p.dias_atraso DESC, p.fecha_vencimiento ASC"
    pagos = query_db(sql, params)

    # Métricas del módulo de morosidad
    total_cartera = query_db("SELECT COUNT(*) as cnt FROM pagos", one=True)['cnt']
    cuotas_en_mora = query_db("SELECT COUNT(*) as cnt FROM pagos WHERE estado_pago = 'EN_MORA'", one=True)['cnt']
    mora_critica = query_db("SELECT COUNT(*) as cnt FROM pagos WHERE dias_atraso > 30", one=True)['cnt']
    monto_vencido = query_db("""
        SELECT SUM(CASE WHEN p.monto_cuota + p.penalidad - COALESCE(
            (SELECT SUM(tp.monto) FROM transacciones_pago tp WHERE tp.cuota_id = p.id), 0
        ) > 0 THEN p.monto_cuota + p.penalidad - COALESCE(
            (SELECT SUM(tp.monto) FROM transacciones_pago tp WHERE tp.cuota_id = p.id), 0
        ) ELSE 0 END) AS sum_mora
        FROM pagos p WHERE p.estado_pago IN ('EN_MORA', 'VENCIDO')
    """, one=True)['sum_mora'] or 0.0

    # Cartera en riesgo (clientes en mora)
    clientes_en_mora = query_db("""
        SELECT DISTINCT c.id, c.codigo_cliente, c.nombres, c.apellidos, c.dni, c.telefono,
               MAX(p.dias_atraso) as max_dias, COUNT(p.id) as cuotas_impagas,
               SUM(CASE WHEN p.monto_cuota + p.penalidad - COALESCE(
                   (SELECT SUM(tp.monto) FROM transacciones_pago tp WHERE tp.cuota_id = p.id), 0
               ) > 0 THEN p.monto_cuota + p.penalidad - COALESCE(
                   (SELECT SUM(tp.monto) FROM transacciones_pago tp WHERE tp.cuota_id = p.id), 0
               ) ELSE 0 END) as deuda_vencida
        FROM pagos p
        JOIN clientes c ON p.cliente_id = c.id
        WHERE p.estado_pago IN ('EN_MORA', 'VENCIDO')
        GROUP BY c.id
        ORDER BY max_dias DESC
    """)

    # Alertas de morosidad
    alertas_morosidad = query_db("""
        SELECT a.*, c.nombres, c.apellidos, c.codigo_cliente
        FROM alertas a
        LEFT JOIN clientes c ON a.cliente_id = c.id
        WHERE a.tipo_alerta LIKE '%Mora%' OR a.severidad IN ('ALTA', 'CRITICA')
        ORDER BY a.created_at DESC
        LIMIT 6
    """)
    promesas_activas = query_db("""
        SELECT id, cliente_id, monto_comprometido, fecha_prometida
        FROM promesas_pago WHERE estado IN ('PENDIENTE', 'VENCIDA', 'INCUMPLIDA')
        ORDER BY fecha_prometida
    """)

    kpis_mora = {
        'total_cartera': total_cartera,
        'cuotas_en_mora': cuotas_en_mora,
        'mora_critica': mora_critica,
        'monto_vencido': monto_vencido,
        'ratio_mora': round((cuotas_en_mora / total_cartera * 100), 1) if total_cartera > 0 else 0
    }

    return render_template(
        'morosidad.html',
        pagos=pagos,
        kpis_mora=kpis_mora,
        clientes_en_mora=clientes_en_mora,
        alertas=alertas_morosidad,
        promesas_activas=promesas_activas,
        estado_filtro=estado_filtro,
        nivel_filtro=nivel_filtro
    )

@morosidad_bp.route('/registrar-pago/<pago_id>', methods=['POST'])
@login_required
@role_required('Administrador', 'Personal de cobranza')
def registrar_pago(pago_id):
    """Registra la cancelación de una cuota vencida o pendiente."""
    metodo = request.form.get('metodo_pago', 'Ventanilla Caja').strip()
    fecha_pago = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    promesa_id = request.form.get("promesa_id", "").strip() or None

    pago = query_db("SELECT * FROM pagos WHERE id = ?", (pago_id,), one=True)
    if not pago:
        flash('Registro de pago no encontrado.', 'danger')
        return redirect(url_for('morosidad.index'))

    already_paid = query_db(
        "SELECT COALESCE(SUM(monto), 0) AS total FROM transacciones_pago WHERE cuota_id = ?",
        (pago_id,), one=True
    )["total"]
    total_due = float(pago["monto_cuota"]) + float(pago["penalidad"] or 0)
    remaining = max(0.0, total_due - float(already_paid or 0))
    try:
        amount = float(request.form.get("monto_pagado", remaining))
    except (TypeError, ValueError):
        amount = 0
    if not math.isfinite(amount) or amount <= 0 or amount > remaining + 0.0001 or not metodo or len(metodo) > 80:
        flash(f'El abono debe ser positivo y no exceder el saldo de S/. {remaining:,.2f}.', 'danger')
        return redirect(url_for('morosidad.index'))

    promise = None
    if promesa_id:
        promise = query_db(
            "SELECT id, cliente_id, estado FROM promesas_pago WHERE id = ?",
            (promesa_id,), one=True
        )
        if not promise or promise["cliente_id"] != pago["cliente_id"] or promise["estado"] not in ("PENDIENTE", "VENCIDA", "INCUMPLIDA"):
            flash("La promesa seleccionada no corresponde al cliente o ya está cerrada.", "danger")
            return redirect(url_for('morosidad.index'))

    fecha_vencimiento = pago['fecha_vencimiento']
    if not isinstance(fecha_vencimiento, date):
        fecha_vencimiento = date.fromisoformat(str(fecha_vencimiento)[:10])
    dias_atraso = max(0, (datetime.now().date() - fecha_vencimiento).days)
    clasificacion = clasificar_dias_mora_sbs(dias_atraso)['categoria']
    fully_paid = float(already_paid or 0) + amount + 0.0001 >= total_due

    execute_transaction([
        ("""
        INSERT INTO transacciones_pago (
            id, cuota_id, solicitud_id, cliente_id, promesa_id, monto,
            metodo_pago, registrado_por, fecha_pago
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            new_id("txn"), pago["id"], pago["solicitud_id"], pago["cliente_id"],
            promesa_id, amount, metodo, session.get("user_id"), fecha_pago,
        )),
        ("""
        UPDATE pagos SET
            estado_pago = ?,
            fecha_pago = ?,
            metodo_pago = ?,
            dias_atraso = ?,
            clasificacion_sbs = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (
            'PAGADO' if fully_paid else ('EN_MORA' if dias_atraso > 0 else pago["estado_pago"]),
            fecha_pago, metodo, dias_atraso, clasificacion, pago_id,
        )),
    ])

    flash(f'Abono de S/. {amount:,.2f} registrado exitosamente.', 'success')
    return redirect(url_for('morosidad.index'))

@morosidad_bp.route('/crear-alerta-preventiva', methods=['POST'])
@login_required
@role_required('Administrador', 'Personal de cobranza')
def crear_alerta():
    """Genera una alerta preventiva de cobranza para un cliente específico."""
    cliente_id = request.form.get('cliente_id')
    tipo_alerta = request.form.get('tipo_alerta', 'Alerta Preventiva de Cobranza')
    severidad = request.form.get('severidad', 'MEDIA')
    mensaje = request.form.get('mensaje', '').strip()
    accion = request.form.get('accion_recomendada', '').strip()

    if not cliente_id or not mensaje:
        flash('Debe seleccionar un cliente y redactar el mensaje de la alerta.', 'warning')
        return redirect(url_for('morosidad.index'))

    alerta_id = new_id("alt")
    execute_db("""
        INSERT INTO alertas (id, cliente_id, tipo_alerta, severidad, mensaje, accion_recomendada)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (alerta_id, cliente_id, tipo_alerta, severidad, mensaje, accion))

    # Notificación a Telegram si la alerta es CRÍTICA
    if severidad == 'CRITICA':
        try:
            from services.telegram_service import enviar_mensaje_telegram, formatear_mensaje_alerta, registrar_notificacion_en_bd, obtener_chat_id_telegram
            cliente = query_db("SELECT codigo_cliente FROM clientes WHERE id = ?", (cliente_id,), one=True)
            codigo_cli = cliente['codigo_cliente'] if cliente else f"CLI-{cliente_id[:8]}"
            msg_tg = formatear_mensaje_alerta(
                codigo_cliente=codigo_cli,
                numero_solicitud="COBRANZA-URGENTE",
                nivel_riesgo="ALTO",
                motivo=mensaje,
                fecha_eval=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            chat_id = obtener_chat_id_telegram()
            res_envio = enviar_mensaje_telegram(msg_tg, chat_id=chat_id)
            registrar_notificacion_en_bd(
                evaluacion_id=None,
                solicitud_id=None,
                cliente_id=cliente_id,
                chat_id=chat_id,
                tipo_alerta="MORA_CRITICA",
                nivel_riesgo="ALTO",
                mensaje=msg_tg,
                estado_envio="ENVIADO" if res_envio.get("enviado") else "FALLIDO",
                reintentos=res_envio.get("intentos", 1),
                error_detalle=res_envio.get("error")
            )
        except Exception as e_tg:
            print(f"[WARN] Error al notificar mora crítica a Telegram: {e_tg}")

    flash('Alerta preventiva generada exitosamente y notificada al equipo de cobranzas.', 'success')
    return redirect(url_for('morosidad.index'))

@morosidad_bp.route('/enviar-recordatorio-telegram/<pago_id>', methods=['POST'])
@login_required
@role_required('Administrador', 'Personal de cobranza')
def enviar_recordatorio_telegram(pago_id):
    """Envía un recordatorio preventivo de pago o aviso formal de mora al Telegram del cliente."""
    from services.telegram_service import enviar_recordatorio_cuota_telegram
    try:
        res = enviar_recordatorio_cuota_telegram(pago_id)
        if res.get("enviado"):
            flash('Recordatorio institucional de pago enviado con éxito a Telegram.', 'success')
        else:
            motivo = res.get("motivo") or res.get("error", "Error en el envío")
            flash(f'No se pudo enviar la notificación a Telegram: {motivo}', 'warning')
    except Exception as e:
        flash(f'Error al procesar el recordatorio para Telegram: {e}', 'danger')

    return redirect(url_for('morosidad.index'))
