from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from routes.auth import login_required, role_required
from database.db import new_id, query_db, execute_db
from services.credit_scoring import (
    calcular_cuota_mensual,
    calcular_capacidad_pago,
    calcular_ratio_dti,
    calcular_ingreso_disponible,
    calcular_scoring_analitico
)

creditos_bp = Blueprint('creditos', __name__, url_prefix='/creditos')

@creditos_bp.route('/')
@login_required
@role_required('Administrador', 'Analista de créditos')
def index():
    estado_filtro = request.args.get('estado', '').strip()
    q = request.args.get('q', '').strip()

    sql = """
        SELECT s.*, c.nombres, c.apellidos, c.dni, c.codigo_cliente, c.ocupacion,
               e.score_riesgo, e.nivel_riesgo as eval_nivel, e.dictamen_humano
        FROM solicitudes_credito s
        JOIN clientes c ON s.cliente_id = c.id
        LEFT JOIN evaluaciones_riesgo e ON s.id = e.solicitud_id
        WHERE 1=1
    """
    params = []

    if estado_filtro:
        sql += " AND s.estado = ?"
        params.append(estado_filtro)

    if q:
        sql += " AND (c.nombres LIKE ? OR c.apellidos LIKE ? OR c.dni LIKE ? OR s.numero_solicitud LIKE ?)"
        term = f"%{q}%"
        params.extend([term, term, term, term])

    sql += " ORDER BY s.created_at DESC"
    solicitudes = query_db(sql, params)
    clientes = query_db("SELECT id, nombres, apellidos, dni, ingresos_mensuales, gastos_mensuales, deudas_actuales FROM clientes WHERE activo = TRUE ORDER BY nombres ASC")

    return render_template(
        'creditos.html',
        solicitudes=solicitudes,
        clientes=clientes,
        estado_filtro=estado_filtro,
        q=q
    )

@creditos_bp.route('/simular', methods=['POST'])
@login_required
@role_required('Administrador', 'Analista de créditos')
def simular():
    """API para la calculadora interactiva de crédito en tiempo real."""
    data = request.get_json() or {}
    try:
        monto = float(data.get('monto', 0))
        plazo = int(data.get('plazo', 12))
        ingresos = float(data.get('ingresos', 0))
        gastos = float(data.get('gastos', 0))
        deudas = float(data.get('deudas', 0))
        tasa = float(data.get('tasa', 0.028)) # 2.8% mensual

        cuota = calcular_cuota_mensual(monto, plazo, tasa)
        capacidad = calcular_capacidad_pago(ingresos, gastos)
        dti = calcular_ratio_dti(deudas, cuota, ingresos)
        disponible = calcular_ingreso_disponible(ingresos, gastos, deudas, cuota)

        # Análisis rápido de viabilidad
        if dti <= 35.0 and disponible > 0:
            semaforo = 'VERDE'
            diagnostico = 'Capacidad financiera saludable. Endeudamiento óptimo.'
        elif dti <= 50.0 and disponible >= 0:
            semaforo = 'AMARILLO'
            diagnostico = 'Endeudamiento moderado. Requiere verificación de ingresos.'
        else:
            semaforo = 'ROJO'
            diagnostico = 'Sobreendeudamiento o déficit de liquidez detectado.'

        return jsonify({
            'success': True,
            'cuota_mensual': cuota,
            'capacidad_pago': capacidad,
            'ratio_dti': dti,
            'ingreso_disponible': disponible,
            'semaforo': semaforo,
            'diagnostico': diagnostico
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@creditos_bp.route('/crear', methods=['POST'])
@login_required
@role_required('Administrador', 'Analista de créditos')
def crear():
    try:
        cliente_id = request.form.get('cliente_id')
        monto = float(request.form.get('monto_solicitado', 0))
        plazo = int(request.form.get('plazo_meses', 12))
        tipo_credito = request.form.get('tipo_credito', 'Microempresa / MYPE')
        historial = request.form.get('historial_pagos', 'Puntual sin atrasos')
        laboral = request.form.get('situacion_laboral', 'Microempresario / Negocio propio')
        tasa = float(request.form.get('tasa_interes_mensual', 0.028))

        # Recuperar datos del cliente
        cliente = query_db("SELECT * FROM clientes WHERE id = ?", (cliente_id,), one=True)
        if not cliente:
            flash('Cliente no encontrado.', 'danger')
            return redirect(url_for('creditos.index'))

        ingresos = float(request.form.get('ingresos_declarados', cliente['ingresos_mensuales']))
        gastos = float(request.form.get('gastos_declarados', cliente['gastos_mensuales']))
        deudas = float(request.form.get('deudas_declaradas', cliente['deudas_actuales']))

        # Cálculos financieros automáticos
        cuota = calcular_cuota_mensual(monto, plazo, tasa)
        capacidad = calcular_capacidad_pago(ingresos, gastos)
        dti = calcular_ratio_dti(deudas, cuota, ingresos)
        disponible = calcular_ingreso_disponible(ingresos, gastos, deudas, cuota)

        # Generar correlativo
        conteo = query_db("SELECT COUNT(*) as cnt FROM solicitudes_credito", one=True)['cnt'] + 1
        numero_solicitud = f"SOL-2024-{conteo:03d}"
        solicitud_id = new_id("sol")

        execute_db("""
            INSERT INTO solicitudes_credito (
                id, numero_solicitud, cliente_id, monto_solicitado, plazo_meses,
                tasa_interes_mensual, cuota_mensual_estimada, tipo_credito,
                historial_pagos, situacion_laboral, ingresos_declarados, gastos_declarados,
                deudas_declaradas, capacidad_pago, ratio_dti, ingreso_disponible, estado
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDIENTE')
        """, (
            solicitud_id, numero_solicitud, cliente_id, monto, plazo,
            tasa, cuota, tipo_credito, historial, laboral,
            ingresos, gastos, deudas, capacidad, dti, disponible
        ))

        flash(f'Solicitud de Crédito {numero_solicitud} registrada exitosamente. Lista para evaluación con IA.', 'success')
        return redirect(url_for('riesgos.evaluar', solicitud_id=solicitud_id))
    except Exception as e:
        flash(f'Error al crear solicitud: {str(e)}', 'danger')
        return redirect(url_for('creditos.index'))
