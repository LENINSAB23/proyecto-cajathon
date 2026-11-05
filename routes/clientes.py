import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from routes.auth import login_required, role_required
from database.db import query_db, execute_db
from services.credit_scoring import calcular_scoring_analitico

clientes_bp = Blueprint('clientes', __name__, url_prefix='/clientes')

@clientes_bp.route('/')
@login_required
def index():
    q = request.args.get('q', '').strip()
    nivel_filtro = request.args.get('nivel', '').strip()

    sql = "SELECT * FROM clientes WHERE activo = 1"
    params = []

    if q:
        sql += " AND (nombres LIKE ? OR apellidos LIKE ? OR dni LIKE ? OR codigo_cliente LIKE ? OR ocupacion LIKE ?)"
        term = f"%{q}%"
        params.extend([term, term, term, term, term])

    if nivel_filtro in ['BAJO', 'MEDIO', 'ALTO']:
        sql += " AND nivel_riesgo = ?"
        params.append(nivel_filtro)

    sql += " ORDER BY created_at DESC"
    clientes = query_db(sql, params)

    return render_template('clientes.html', clientes=clientes, q=q, nivel_filtro=nivel_filtro)

@clientes_bp.route('/crear', methods=['POST'])
@login_required
@role_required('Administrador', 'Analista de créditos')
def crear():
    try:
        nombres = request.form.get('nombres', '').strip()
        apellidos = request.form.get('apellidos', '').strip()
        dni = request.form.get('dni', '').strip()
        edad = int(request.form.get('edad', 30))
        ocupacion = request.form.get('ocupacion', '').strip()
        sector = request.form.get('sector_economico', 'Comercio').strip()
        ingresos = float(request.form.get('ingresos_mensuales', 0))
        gastos = float(request.form.get('gastos_mensuales', 0))
        deudas = float(request.form.get('deudas_actuales', 0))
        telefono = request.form.get('telefono', '').strip()
        email = request.form.get('email', '').strip()
        direccion = request.form.get('direccion', '').strip()
        departamento = request.form.get('departamento', 'Lima').strip()

        # Validaciones
        if not (nombres and apellidos and dni and len(dni) == 8 and dni.isdigit()):
            flash('Por favor complete todos los datos obligatorios. El DNI debe tener 8 dígitos numéricos.', 'danger')
            return redirect(url_for('clientes.index'))

        # Verificar duplicado de DNI
        existente = query_db("SELECT id FROM clientes WHERE dni = ?", (dni,), one=True)
        if existente:
            flash(f'El DNI {dni} ya se encuentra registrado en el sistema.', 'warning')
            return redirect(url_for('clientes.index'))

        # Generar código correlativo
        conteo = query_db("SELECT COUNT(*) as cnt FROM clientes", one=True)['cnt'] + 1
        codigo_cliente = f"CLI-2024-{conteo:03d}"
        cliente_id = f"cli-{uuid.uuid4().hex[:8]}"

        # Evaluación financiera preliminar
        scoring = calcular_scoring_analitico({
            'ingresos_mensuales': ingresos,
            'gastos_mensuales': gastos,
            'deudas_actuales': deudas,
            'monto_solicitado': 5000,
            'plazo_meses': 12
        })

        execute_db("""
            INSERT INTO clientes (
                id, codigo_cliente, nombres, apellidos, dni, edad, ocupacion, 
                sector_economico, ingresos_mensuales, gastos_mensuales, deudas_actuales, 
                score_interno, nivel_riesgo, telefono, email, direccion, departamento
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cliente_id, codigo_cliente, nombres, apellidos, dni, edad, ocupacion,
            sector, ingresos, gastos, deudas, scoring['score_riesgo'], scoring['nivel_riesgo'],
            telefono, email, direccion, departamento
        ))

        flash(f'Cliente {nombres} {apellidos} ({codigo_cliente}) registrado exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al registrar cliente: {str(e)}', 'danger')

    return redirect(url_for('clientes.index'))

@clientes_bp.route('/<id>/detalle')
@login_required
def detalle(id):
    cliente = query_db("SELECT * FROM clientes WHERE id = ?", (id,), one=True)
    if not cliente:
        flash('Cliente no encontrado.', 'warning')
        return redirect(url_for('clientes.index'))

    # Solicitudes del cliente
    solicitudes = query_db("SELECT * FROM solicitudes_credito WHERE cliente_id = ? ORDER BY created_at DESC", (id,))
    # Historial de pagos
    pagos = query_db("SELECT * FROM pagos WHERE cliente_id = ? ORDER BY fecha_vencimiento DESC", (id,))
    # Historial crediticio en otras entidades
    historial = query_db("SELECT * FROM historial_crediticio WHERE cliente_id = ? ORDER BY created_at DESC", (id,))
    # Alertas asociadas
    alertas = query_db("SELECT * FROM alertas WHERE cliente_id = ? ORDER BY created_at DESC", (id,))

    return render_template(
        'cliente_detalle.html',
        cliente=cliente,
        solicitudes=solicitudes,
        pagos=pagos,
        historial=historial,
        alertas=alertas
    )

@clientes_bp.route('/<id>/editar', methods=['POST'])
@login_required
@role_required('Administrador', 'Analista de créditos')
def editar(id):
    try:
        nombres = request.form.get('nombres', '').strip()
        apellidos = request.form.get('apellidos', '').strip()
        edad = int(request.form.get('edad', 30))
        ocupacion = request.form.get('ocupacion', '').strip()
        sector = request.form.get('sector_economico', 'Comercio').strip()
        ingresos = float(request.form.get('ingresos_mensuales', 0))
        gastos = float(request.form.get('gastos_mensuales', 0))
        deudas = float(request.form.get('deudas_actuales', 0))
        telefono = request.form.get('telefono', '').strip()
        email = request.form.get('email', '').strip()
        direccion = request.form.get('direccion', '').strip()
        departamento = request.form.get('departamento', 'Lima').strip()

        # Recalcular score preliminar
        scoring = calcular_scoring_analitico({
            'ingresos_mensuales': ingresos,
            'gastos_mensuales': gastos,
            'deudas_actuales': deudas,
            'monto_solicitado': 5000,
            'plazo_meses': 12
        })

        execute_db("""
            UPDATE clientes SET
                nombres = ?, apellidos = ?, edad = ?, ocupacion = ?, sector_economico = ?,
                ingresos_mensuales = ?, gastos_mensuales = ?, deudas_actuales = ?,
                score_interno = ?, nivel_riesgo = ?, telefono = ?, email = ?,
                direccion = ?, departamento = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            nombres, apellidos, edad, ocupacion, sector,
            ingresos, gastos, deudas, scoring['score_riesgo'], scoring['nivel_riesgo'],
            telefono, email, direccion, departamento, id
        ))

        flash('Información del cliente actualizada correctamente.', 'success')
    except Exception as e:
        flash(f'Error al actualizar: {str(e)}', 'danger')

    return redirect(url_for('clientes.index'))

@clientes_bp.route('/<id>/eliminar', methods=['POST'])
@login_required
@role_required('Administrador')
def eliminar(id):
    cliente = query_db("SELECT nombres, apellidos FROM clientes WHERE id = ?", (id,), one=True)
    if cliente:
        execute_db("DELETE FROM clientes WHERE id = ?", (id,))
        flash(f'El cliente {cliente["nombres"]} {cliente["apellidos"]} ha sido eliminado del sistema.', 'info')
    else:
        flash('Cliente no encontrado.', 'warning')
    return redirect(url_for('clientes.index'))

