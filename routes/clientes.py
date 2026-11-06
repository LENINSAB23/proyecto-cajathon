import math

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from routes.auth import login_required, role_required
from database.db import new_id, query_db, execute_db
from services.credit_scoring import calcular_scoring_analitico

clientes_bp = Blueprint('clientes', __name__, url_prefix='/clientes')

def _datos_financieros_validos(edad, ingresos, gastos, deudas):
    return (
        18 <= edad <= 95
        and all(math.isfinite(value) for value in (ingresos, gastos, deudas))
        and ingresos > 0
        and gastos >= 0
        and deudas >= 0
    )


def _geographic_fields():
    department = request.form.get('departamento', '').strip() or None
    province = request.form.get('provincia', '').strip() or None
    district = request.form.get('distrito', '').strip() or None
    raw_latitude = request.form.get('latitud', '').strip()
    raw_longitude = request.form.get('longitud', '').strip()
    if bool(raw_latitude) != bool(raw_longitude):
        raise ValueError("Ingrese ambas coordenadas o deje ambas vacías.")
    if not raw_latitude:
        return department, province, district, None, None
    latitude, longitude = float(raw_latitude), float(raw_longitude)
    if not (-18.5 <= latitude <= 0 and -82 <= longitude <= -68):
        raise ValueError("Las coordenadas deben corresponder al rango geográfico del Perú.")
    return department, province, district, latitude, longitude

@clientes_bp.route('/')
@login_required
@role_required('Administrador', 'Analista de créditos')
def index():
    q = request.args.get('q', '').strip()
    nivel_filtro = request.args.get('nivel', '').strip()

    sql = "SELECT * FROM clientes WHERE activo = TRUE"
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
        departamento, provincia, distrito, latitud, longitud = _geographic_fields()

        # Validaciones
        if not (nombres and apellidos and dni and len(dni) == 8 and dni.isdigit()):
            flash('Por favor complete todos los datos obligatorios. El DNI debe tener 8 dígitos numéricos.', 'danger')
            return redirect(url_for('clientes.index'))
        if not ocupacion or not _datos_financieros_validos(edad, ingresos, gastos, deudas):
            flash('La edad debe estar entre 18 y 95 años y los ingresos/gastos/deudas deben ser válidos.', 'danger')
            return redirect(url_for('clientes.index'))

        # Verificar duplicado de DNI
        existente = query_db("SELECT id FROM clientes WHERE dni = ?", (dni,), one=True)
        if existente:
            flash(f'El DNI {dni} ya se encuentra registrado en el sistema.', 'warning')
            return redirect(url_for('clientes.index'))

        # Generar código correlativo
        conteo = query_db("SELECT COUNT(*) as cnt FROM clientes", one=True)['cnt'] + 1
        codigo_cliente = f"CLI-2024-{conteo:03d}"
        cliente_id = new_id("cli")

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
                , provincia, distrito, latitud, longitud
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cliente_id, codigo_cliente, nombres, apellidos, dni, edad, ocupacion,
            sector, ingresos, gastos, deudas, scoring['score_riesgo'], scoring['nivel_riesgo'],
            telefono, email, direccion, departamento, provincia, distrito, latitud, longitud
        ))

        flash(f'Cliente {nombres} {apellidos} ({codigo_cliente}) registrado exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al registrar cliente: {str(e)}', 'danger')

    return redirect(url_for('clientes.index'))

@clientes_bp.route('/<id>/detalle')
@login_required
@role_required('Administrador', 'Analista de créditos')
def detalle(id):
    cliente = query_db("SELECT * FROM clientes WHERE id = ?", (id,), one=True)
    if not cliente:
        flash('Cliente no encontrado.', 'warning')
        return redirect(url_for('clientes.index'))

    # Solicitudes del cliente
    solicitudes = query_db("SELECT * FROM solicitudes_credito WHERE cliente_id = ? ORDER BY created_at DESC", (id,))
    # Historial de pagos
    pagos = query_db("SELECT * FROM pagos WHERE cliente_id = ? ORDER BY fecha_vencimiento DESC", (id,))
    transacciones_pago = query_db("""
        SELECT t.*, p.numero_cuota, p.total_cuotas
        FROM transacciones_pago t
        JOIN pagos p ON p.id = t.cuota_id
        WHERE t.cliente_id = ?
        ORDER BY t.fecha_pago DESC
    """, (id,))
    # Historial crediticio en otras entidades
    historial = query_db("SELECT * FROM historial_crediticio WHERE cliente_id = ? ORDER BY created_at DESC", (id,))
    # Alertas asociadas
    alertas = query_db("SELECT * FROM alertas WHERE cliente_id = ? ORDER BY created_at DESC", (id,))

    return render_template(
        'cliente_detalle.html',
        cliente=cliente,
        solicitudes=solicitudes,
        pagos=pagos,
        transacciones_pago=transacciones_pago,
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
        departamento, provincia, distrito, latitud, longitud = _geographic_fields()

        if not (nombres and apellidos and ocupacion) or not _datos_financieros_validos(edad, ingresos, gastos, deudas):
            flash('Complete los datos obligatorios y verifique edad e información financiera.', 'danger')
            return redirect(url_for('clientes.index'))

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
                direccion = ?, departamento = ?, provincia = ?, distrito = ?,
                latitud = ?, longitud = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            nombres, apellidos, edad, ocupacion, sector,
            ingresos, gastos, deudas, scoring['score_riesgo'], scoring['nivel_riesgo'],
            telefono, email, direccion, departamento, provincia, distrito, latitud, longitud, id
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
        retained_records = query_db(
            """SELECT id FROM historial_decisiones WHERE cliente_id = ?
               UNION ALL
               SELECT id FROM transacciones_pago WHERE cliente_id = ?
               UNION ALL
               SELECT id FROM promesas_pago WHERE cliente_id = ?
               LIMIT 1""",
            (id, id, id), one=True
        )
        if retained_records:
            flash(
                'No se puede eliminar el cliente porque tiene decisiones auditables o pagos registrados. '
                'Los registros financieros deben conservarse.',
                'warning'
            )
            return redirect(url_for('clientes.index'))
        execute_db("DELETE FROM clientes WHERE id = ?", (id,))
        flash(f'El cliente {cliente["nombres"]} {cliente["apellidos"]} ha sido eliminado del sistema.', 'info')
    else:
        flash('Cliente no encontrado.', 'warning')
    return redirect(url_for('clientes.index'))
