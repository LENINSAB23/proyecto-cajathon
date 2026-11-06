from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from routes.auth import login_required, role_required
from database.db import new_id, query_db, execute_db
from services.credit_scoring import clasificar_dias_mora_sbs

morosidad_bp = Blueprint('morosidad', __name__, url_prefix='/morosidad')

@morosidad_bp.route('/')
@login_required
@role_required('Administrador', 'Personal de cobranza')
def index():
    estado_filtro = request.args.get('estado', '').strip()
    nivel_filtro = request.args.get('clasificacion', '').strip()

    sql = """
        SELECT p.*, c.nombres, c.apellidos, c.dni, c.codigo_cliente, c.telefono, c.ocupacion,
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
    monto_vencido = query_db("SELECT SUM(monto_cuota + penalidad) as sum_mora FROM pagos WHERE estado_pago IN ('EN_MORA', 'VENCIDO')", one=True)['sum_mora'] or 0.0

    # Cartera en riesgo (clientes en mora)
    clientes_en_mora = query_db("""
        SELECT DISTINCT c.id, c.codigo_cliente, c.nombres, c.apellidos, c.dni, c.telefono,
               MAX(p.dias_atraso) as max_dias, COUNT(p.id) as cuotas_impagas,
               SUM(p.monto_cuota) as deuda_vencida
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
        estado_filtro=estado_filtro,
        nivel_filtro=nivel_filtro
    )

@morosidad_bp.route('/registrar-pago/<pago_id>', methods=['POST'])
@login_required
@role_required('Administrador', 'Personal de cobranza')
def registrar_pago(pago_id):
    """Registra la cancelación de una cuota vencida o pendiente."""
    metodo = request.form.get('metodo_pago', 'Ventanilla Caja')
    fecha_pago = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    pago = query_db("SELECT * FROM pagos WHERE id = ?", (pago_id,), one=True)
    if not pago:
        flash('Registro de pago no encontrado.', 'danger')
        return redirect(url_for('morosidad.index'))

    fecha_vencimiento = pago['fecha_vencimiento']
    if not isinstance(fecha_vencimiento, date):
        fecha_vencimiento = date.fromisoformat(fecha_vencimiento[:10])
    dias_atraso = max(0, (datetime.now().date() - fecha_vencimiento).days)
    clasificacion = clasificar_dias_mora_sbs(dias_atraso)['categoria']

    execute_db("""
        UPDATE pagos SET
            estado_pago = 'PAGADO',
            fecha_pago = ?,
            metodo_pago = ?,
            dias_atraso = ?,
            clasificacion_sbs = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (fecha_pago, metodo, dias_atraso, clasificacion, pago_id))

    flash(f'Pago de cuota N° {pago["numero_cuota"]} por S/. {pago["monto_cuota"]:,.2f} registrado exitosamente.', 'success')
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

    flash('Alerta preventiva generada exitosamente y notificada al equipo de cobranzas.', 'success')
    return redirect(url_for('morosidad.index'))
