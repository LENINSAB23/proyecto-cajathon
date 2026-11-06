import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from routes.auth import login_required, role_required
from database.db import new_id, query_db, execute_db
from services.ia_service import analizar_riesgo_con_ia

riesgos_bp = Blueprint('riesgos', __name__, url_prefix='/riesgos')

def _read_json_list(value):
    if isinstance(value, list):
        return value
    if not value:
        return []
    parsed = json.loads(value)
    return parsed if isinstance(parsed, list) else []

@riesgos_bp.route('/')
@login_required
@role_required('Administrador', 'Analista de créditos')
def index():
    """Matriz de Riesgo y Cartera Evaluada."""
    filtro_nivel = request.args.get('nivel', '').strip()
    
    sql = """
        SELECT e.*, s.numero_solicitud, s.monto_solicitado, s.plazo_meses, s.tipo_credito, s.estado as estado_solicitud,
               c.nombres, c.apellidos, c.dni, c.codigo_cliente, c.ocupacion
        FROM evaluaciones_riesgo e
        JOIN solicitudes_credito s ON e.solicitud_id = s.id
        JOIN clientes c ON e.cliente_id = c.id
        WHERE 1=1
    """
    params = []
    if filtro_nivel in ['BAJO', 'MEDIO', 'ALTO']:
        sql += " AND e.nivel_riesgo = ?"
        params.append(filtro_nivel)

    sql += " ORDER BY e.created_at DESC"
    evaluaciones = query_db(sql, params)

    # Métricas agregadas de riesgo
    total_eval = len(evaluaciones)
    bajo_cnt = sum(1 for e in evaluaciones if e['nivel_riesgo'] == 'BAJO')
    medio_cnt = sum(1 for e in evaluaciones if e['nivel_riesgo'] == 'MEDIO')
    alto_cnt = sum(1 for e in evaluaciones if e['nivel_riesgo'] == 'ALTO')

    return render_template(
        'riesgos_matriz.html',
        evaluaciones=evaluaciones,
        filtro_nivel=filtro_nivel,
        total_eval=total_eval,
        bajo_cnt=bajo_cnt,
        medio_cnt=medio_cnt,
        alto_cnt=alto_cnt
    )

@riesgos_bp.route('/evaluar/<solicitud_id>')
@login_required
@role_required('Administrador', 'Analista de créditos')
def evaluar(solicitud_id):
    """Página de evaluación con IA para una solicitud específica."""
    solicitud = query_db("""
        SELECT s.*, c.nombres, c.apellidos, c.dni, c.edad, c.ocupacion, c.sector_economico,
               c.telefono, c.email, c.direccion, c.codigo_cliente, c.score_interno
        FROM solicitudes_credito s
        JOIN clientes c ON s.cliente_id = c.id
        WHERE s.id = ?
    """, (solicitud_id,), one=True)

    if not solicitud:
        flash('Solicitud no encontrada.', 'danger')
        return redirect(url_for('creditos.index'))

    # Buscar si ya tiene evaluación previa
    evaluacion = query_db("SELECT * FROM evaluaciones_riesgo WHERE solicitud_id = ?", (solicitud_id,), one=True)

    factores_pos = []
    factores_neg = []
    alertas_ia = []
    if evaluacion:
        factores_pos = _read_json_list(evaluacion.get('factores_positivos'))
        factores_neg = _read_json_list(evaluacion.get('factores_negativos'))
        alertas_ia = _read_json_list(evaluacion.get('senales_alerta'))

    return render_template(
        'evaluacion.html',
        solicitud=solicitud,
        evaluacion=evaluacion,
        factores_pos=factores_pos,
        factores_neg=factores_neg,
        alertas_ia=alertas_ia
    )

@riesgos_bp.route('/procesar-ia/<solicitud_id>', methods=['POST'])
@login_required
@role_required('Administrador', 'Analista de créditos')
def procesar_ia(solicitud_id):
    """Ejecuta el análisis de IA (OpenAI o Motor Demo) y guarda la evaluación en la base de datos."""
    solicitud = query_db("""
        SELECT s.*, c.nombres, c.apellidos, c.dni, c.edad, c.ocupacion, c.sector_economico,
               c.id as cliente_real_id, c.codigo_cliente
        FROM solicitudes_credito s
        JOIN clientes c ON s.cliente_id = c.id
        WHERE s.id = ?
    """, (solicitud_id,), one=True)

    if not solicitud:
        flash('Solicitud no encontrada.', 'danger')
        return redirect(url_for('creditos.index'))

    datos_cliente = {
        'id': solicitud['cliente_real_id'],
        'nombres': solicitud['nombres'],
        'apellidos': solicitud['apellidos'],
        'dni': solicitud['dni'],
        'edad': solicitud['edad'],
        'ocupacion': solicitud['ocupacion'],
        'sector_economico': solicitud['sector_economico']
    }

    # Invocación al servicio de Inteligencia Artificial
    resultado = analizar_riesgo_con_ia(solicitud, datos_cliente)

    eval_existente = query_db("SELECT id FROM evaluaciones_riesgo WHERE solicitud_id = ?", (solicitud_id,), one=True)
    eval_id = eval_existente['id'] if eval_existente else new_id("eval")

    analista_nombre = session.get('user_name', 'Analista de Créditos')

    if eval_existente:
        execute_db("""
            UPDATE evaluaciones_riesgo SET
                score_riesgo = ?, nivel_riesgo = ?, resumen_evaluacion = ?,
                factores_positivos = ?, factores_negativos = ?, senales_alerta = ?,
                probabilidad_morosidad_30d = ?, probabilidad_morosidad_90d = ?,
                recomendaciones = ?, modelo_ia_utilizado = ?, es_modo_demo = ?,
                evaluado_por = ?, created_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            resultado['score_riesgo'], resultado['nivel_riesgo'], resultado['resumen_evaluacion'],
            json.dumps(resultado['factores_positivos']), json.dumps(resultado['factores_negativos']),
            json.dumps(resultado['senales_alerta']), resultado['probabilidad_morosidad_30d'],
            resultado['probabilidad_morosidad_90d'], resultado['recomendaciones'],
            resultado['modelo_ia_utilizado'], bool(resultado['es_modo_demo']),
            analista_nombre, eval_id
        ))
    else:
        execute_db("""
            INSERT INTO evaluaciones_riesgo (
                id, solicitud_id, cliente_id, score_riesgo, nivel_riesgo,
                resumen_evaluacion, factores_positivos, factores_negativos,
                senales_alerta, probabilidad_morosidad_30d, probabilidad_morosidad_90d,
                recomendaciones, modelo_ia_utilizado, es_modo_demo, evaluado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            eval_id, solicitud_id, solicitud['cliente_id'], resultado['score_riesgo'],
            resultado['nivel_riesgo'], resultado['resumen_evaluacion'],
            json.dumps(resultado['factores_positivos']), json.dumps(resultado['factores_negativos']),
            json.dumps(resultado['senales_alerta']), resultado['probabilidad_morosidad_30d'],
            resultado['probabilidad_morosidad_90d'], resultado['recomendaciones'],
            resultado['modelo_ia_utilizado'], bool(resultado['es_modo_demo']),
            analista_nombre
        ))

    # Actualizar estado de solicitud y perfil del cliente
    execute_db("UPDATE solicitudes_credito SET estado = 'EVALUADO' WHERE id = ? AND estado = 'PENDIENTE'", (solicitud_id,))
    execute_db("UPDATE clientes SET score_interno = ?, nivel_riesgo = ? WHERE id = ?", (resultado['score_riesgo'], resultado['nivel_riesgo'], solicitud['cliente_id']))

    # Si se detectó riesgo alto o señales críticas, emitir alerta automática
    if resultado['nivel_riesgo'] == 'ALTO' or solicitud['ratio_dti'] > 50:
        alerta_id = new_id("alt")
        execute_db("""
            INSERT INTO alertas (id, cliente_id, solicitud_id, tipo_alerta, severidad, mensaje, accion_recomendada)
            VALUES (?, ?, ?, 'Alerta IA: Riesgo Alto Detectado', 'ALTA', ?, ?)
        """, (
            alerta_id, solicitud['cliente_id'], solicitud_id,
            f"La IA identificó alto riesgo para el cliente {solicitud['nombres']} {solicitud['apellidos']} con Score {resultado['score_riesgo']}/100 y DTI {solicitud['ratio_dti']}%.",
            resultado['recomendaciones'][:200]
        ))

    # ENVÍO AUTOMÁTICO A TELEGRAM: Detección y notificación automática de riesgo alto
    try:
        from services.telegram_service import procesar_alerta_riesgo_automatica
        datos_eval_notif = {
            'id': eval_id,
            'nivel_riesgo': resultado['nivel_riesgo'],
            'score_riesgo': resultado['score_riesgo'],
            'senales_alerta': resultado.get('senales_alerta'),
            'factores_negativos': resultado.get('factores_negativos'),
            'resumen_evaluacion': resultado.get('resumen_evaluacion'),
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        datos_cli_notif = {
            'id': solicitud['cliente_id'],
            'codigo_cliente': solicitud.get('codigo_cliente') or f"CLI-{solicitud['cliente_id'][:8]}"
        }
        res_tg = procesar_alerta_riesgo_automatica(
            datos_evaluacion=datos_eval_notif,
            datos_solicitud=solicitud,
            datos_cliente=datos_cli_notif
        )
        if res_tg.get("alerta_emitida"):
            print(f"[INFO] Alerta Telegram enviada automáticamente para solicitud {solicitud.get('numero_solicitud')}")
    except Exception as e_tg:
        print(f"[WARN] No se pudo procesar alerta de Telegram: {e_tg}")

    flash(f'Análisis de Inteligencia Artificial completado con éxito ({resultado["modelo_ia_utilizado"]}). Riesgo asignado: {resultado["nivel_riesgo"]} (Score: {resultado["score_riesgo"]}).', 'success')
    return redirect(url_for('riesgos.evaluar', solicitud_id=solicitud_id))

@riesgos_bp.route('/dictamen-humano/<solicitud_id>', methods=['POST'])
@login_required
@role_required('Administrador', 'Analista de créditos')
def dictamen_humano(solicitud_id):
    """Registra la decisión final humana del analista de créditos conforme a normas SBS."""
    decision = request.form.get('dictamen_humano') # 'CONFORME', 'REQUIERE_GARANTIA', 'DENEGADO'
    observaciones = request.form.get('observaciones_analista', '').strip()

    estado_map = {
        'CONFORME': 'APROBADO',
        'REQUIERE_GARANTIA': 'OBSERVADO',
        'DENEGADO': 'RECHAZADO'
    }
    nuevo_estado = estado_map.get(decision, 'OBSERVADO')

    execute_db("""
        UPDATE evaluaciones_riesgo SET
            dictamen_humano = ?, observaciones_analista = ?
        WHERE solicitud_id = ?
    """, (decision, observaciones, solicitud_id))

    execute_db("""
        UPDATE solicitudes_credito SET
            estado = ?, motivo_rechazo = ?
        WHERE id = ?
    """, (nuevo_estado, observaciones if nuevo_estado == 'RECHAZADO' else None, solicitud_id))

    flash(f'Dictamen humano registrado con éxito: Solicitud actualizada a estado {nuevo_estado}.', 'success')
    return redirect(url_for('riesgos.evaluar', solicitud_id=solicitud_id))

@riesgos_bp.route('/bank-ito/chat', methods=['POST'])
@login_required
def bankito_chat():
    """Endpoint interactivo para conversar con Bank-ito Copilot."""
    from services.ia_service import consultar_bankito_copilot
    data = request.get_json(silent=True) or {}
    pregunta = data.get('mensaje', '').strip()
    contexto = data.get('contexto', {})
    
    if not pregunta:
        return jsonify({'success': False, 'error': 'Mensaje vacío'}), 400
        
    respuesta = consultar_bankito_copilot(pregunta, contexto=contexto)
    return jsonify({
        'success': True,
        'respuesta': respuesta,
        'autor': 'Bank-ito Copilot',
        'modelo': 'Google Gemini / SBS AI'
    })
