from flask import Blueprint, render_template, jsonify
from routes.auth import login_required
from database.db import query_db

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    # 1. Total clientes registrados
    total_clientes = query_db("SELECT COUNT(*) as total FROM clientes WHERE activo = 1", one=True)['total']

    # 2. Total solicitudes de crédito y desglose de estados
    total_solicitudes = query_db("SELECT COUNT(*) as total FROM solicitudes_credito", one=True)['total']
    aprobados = query_db("SELECT COUNT(*) as total FROM solicitudes_credito WHERE estado = 'APROBADO'", one=True)['total']
    pendientes = query_db("SELECT COUNT(*) as total FROM solicitudes_credito WHERE estado IN ('PENDIENTE', 'EVALUADO')", one=True)['total']
    observados = query_db("SELECT COUNT(*) as total FROM solicitudes_credito WHERE estado = 'OBSERVADO'", one=True)['total']
    rechazados = query_db("SELECT COUNT(*) as total FROM solicitudes_credito WHERE estado = 'RECHAZADO'", one=True)['total']

    # 3. Clientes con riesgo alto
    clientes_riesgo_alto = query_db("SELECT COUNT(*) as total FROM clientes WHERE nivel_riesgo = 'ALTO' AND activo = 1", one=True)['total']

    # 4. Cálculo de Morosidad
    # Total de cuotas vencidas o en mora vs total de cuotas exigibles
    total_cuotas = query_db("SELECT COUNT(*) as total FROM pagos", one=True)['total']
    cuotas_mora = query_db("SELECT COUNT(*) as total FROM pagos WHERE estado_pago IN ('EN_MORA', 'VENCIDO')", one=True)['total']
    
    porcentaje_morosidad = round((cuotas_mora / total_cuotas * 100.0), 2) if total_cuotas > 0 else 0.0

    # 5. Distribución de Riesgos para gráfico
    dist_riesgo = {
        'BAJO': query_db("SELECT COUNT(*) as total FROM clientes WHERE nivel_riesgo = 'BAJO'", one=True)['total'],
        'MEDIO': query_db("SELECT COUNT(*) as total FROM clientes WHERE nivel_riesgo = 'MEDIO'", one=True)['total'],
        'ALTO': query_db("SELECT COUNT(*) as total FROM clientes WHERE nivel_riesgo = 'ALTO'", one=True)['total']
    }

    # 6. Alertas importantes recientes
    alertas_recientes = query_db("""
        SELECT a.*, c.nombres, c.apellidos, c.dni, c.codigo_cliente
        FROM alertas a
        LEFT JOIN clientes c ON a.cliente_id = c.id
        ORDER BY CASE a.severidad 
            WHEN 'CRITICA' THEN 1 
            WHEN 'ALTA' THEN 2 
            WHEN 'MEDIA' THEN 3 
            ELSE 4 END, a.created_at DESC
        LIMIT 5
    """)

    # 7. Actividad reciente: Últimas solicitudes registradas
    actividad_reciente = query_db("""
        SELECT s.*, c.nombres, c.apellidos, c.dni, c.codigo_cliente, c.nivel_riesgo
        FROM solicitudes_credito s
        JOIN clientes c ON s.cliente_id = c.id
        ORDER BY s.created_at DESC
        LIMIT 6
    """)

    # 8. Total colocaciones estimadas aprobadas
    total_colocado = query_db("SELECT SUM(monto_solicitado) as suma FROM solicitudes_credito WHERE estado = 'APROBADO'", one=True)['suma'] or 0.0

    kpis = {
        'total_clientes': total_clientes,
        'total_solicitudes': total_solicitudes,
        'aprobados': aprobados,
        'pendientes': pendientes,
        'observados': observados,
        'rechazados': rechazados,
        'clientes_riesgo_alto': clientes_riesgo_alto,
        'porcentaje_morosidad': porcentaje_morosidad,
        'total_colocado': total_colocado,
        'cuotas_mora': cuotas_mora
    }

    return render_template(
        'dashboard.html',
        kpis=kpis,
        dist_riesgo=dist_riesgo,
        alertas=alertas_recientes,
        actividad=actividad_reciente
    )

@dashboard_bp.route('/api/dashboard/chart-data')
@login_required
def chart_data():
    """Endpoint JSON para alimentar los gráficos de Chart.js con datos dinámicos."""
    # Distribución de Riesgos
    bajo = query_db("SELECT COUNT(*) as cnt FROM clientes WHERE nivel_riesgo = 'BAJO'", one=True)['cnt']
    medio = query_db("SELECT COUNT(*) as cnt FROM clientes WHERE nivel_riesgo = 'MEDIO'", one=True)['cnt']
    alto = query_db("SELECT COUNT(*) as cnt FROM clientes WHERE nivel_riesgo = 'ALTO'", one=True)['cnt']

    # Solicitudes por Mes (simulado dinámicamente)
    meses = ['Jun', 'Jul', 'Ago', 'Set', 'Oct', 'Nov']
    montos_solicitados = [35000, 48000, 62000, 75000, 89000, 115000]
    montos_aprobados = [28000, 39000, 51000, 64000, 71000, 92000]

    return jsonify({
        'distribucion_riesgos': {
            'labels': ['Riesgo Bajo (Apto)', 'Riesgo Medio (Observado)', 'Riesgo Alto (Crítico)'],
            'data': [bajo, medio, alto],
            'colors': ['#10B981', '#F59E0B', '#EF4444']
        },
        'solicitudes_mensuales': {
            'labels': meses,
            'solicitado': montos_solicitados,
            'aprobado': montos_aprobados
        }
    })

