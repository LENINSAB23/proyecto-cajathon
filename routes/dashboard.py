from datetime import datetime
from flask import Blueprint, render_template, jsonify
from routes.auth import login_required, role_required
from database.db import query_db
from config import Config

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
@role_required('Administrador', 'Analista de créditos')
def index():
    # 1. Total clientes registrados
    total_clientes = query_db("SELECT COUNT(*) as total FROM clientes WHERE activo = TRUE", one=True)['total']

    # 2. Total solicitudes de crédito y desglose de estados
    total_solicitudes = query_db("SELECT COUNT(*) as total FROM solicitudes_credito", one=True)['total']
    aprobados = query_db("SELECT COUNT(*) as total FROM solicitudes_credito WHERE estado = 'APROBADO'", one=True)['total']
    pendientes = query_db("SELECT COUNT(*) as total FROM solicitudes_credito WHERE estado IN ('PENDIENTE', 'EVALUADO')", one=True)['total']
    observados = query_db("SELECT COUNT(*) as total FROM solicitudes_credito WHERE estado = 'OBSERVADO'", one=True)['total']
    rechazados = query_db("SELECT COUNT(*) as total FROM solicitudes_credito WHERE estado = 'RECHAZADO'", one=True)['total']

    # 3. Clientes con riesgo alto
    clientes_riesgo_alto = query_db("SELECT COUNT(*) as total FROM clientes WHERE nivel_riesgo = 'ALTO' AND activo = TRUE", one=True)['total']

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
@role_required('Administrador', 'Analista de créditos')
def chart_data():
    """Endpoint JSON para alimentar los gráficos de Chart.js con datos dinámicos."""
    # Distribución de Riesgos
    bajo = query_db("SELECT COUNT(*) as cnt FROM clientes WHERE nivel_riesgo = 'BAJO'", one=True)['cnt']
    medio = query_db("SELECT COUNT(*) as cnt FROM clientes WHERE nivel_riesgo = 'MEDIO'", one=True)['cnt']
    alto = query_db("SELECT COUNT(*) as cnt FROM clientes WHERE nivel_riesgo = 'ALTO'", one=True)['cnt']

    if Config.DATABASE_URL:
        monthly_rows = query_db("""
            SELECT TO_CHAR(fecha_solicitud, 'YYYY-MM') as mes,
                   SUM(monto_solicitado) as solicitado,
                   SUM(CASE WHEN estado = 'APROBADO' THEN monto_solicitado ELSE 0 END) as aprobado
            FROM solicitudes_credito
            WHERE fecha_solicitud >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '5 months'
            GROUP BY TO_CHAR(fecha_solicitud, 'YYYY-MM')
        """)
    else:
        monthly_rows = query_db("""
            SELECT STRFTIME('%Y-%m', fecha_solicitud) as mes,
                   SUM(monto_solicitado) as solicitado,
                   SUM(CASE WHEN estado = 'APROBADO' THEN monto_solicitado ELSE 0 END) as aprobado
            FROM solicitudes_credito
            WHERE DATETIME(fecha_solicitud) >= DATETIME('now', 'start of month', '-5 months')
            GROUP BY STRFTIME('%Y-%m', fecha_solicitud)
        """)

    month_names = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Set', 'Oct', 'Nov', 'Dic']
    month_keys = []
    today = datetime.now()
    current_year, current_month = today.year, today.month
    for offset in range(5, -1, -1):
        month_index = current_year * 12 + current_month - 1 - offset
        year, month_zero_based = divmod(month_index, 12)
        month_keys.append(f"{year:04d}-{month_zero_based + 1:02d}")

    monthly_totals = {
        row['mes']: (float(row['solicitado'] or 0), float(row['aprobado'] or 0))
        for row in monthly_rows
    }
    meses = [month_names[int(key[5:7]) - 1] for key in month_keys]
    montos_solicitados = [monthly_totals.get(key, (0, 0))[0] for key in month_keys]
    montos_aprobados = [monthly_totals.get(key, (0, 0))[1] for key in month_keys]

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
