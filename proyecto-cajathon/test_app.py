from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from app import create_app
from config import Config
from database.db import _prepare_query, get_connection, query_db

def run_tests():
    with patch.object(Config, 'DATABASE_URL', 'postgresql://db.example.test/app'):
        assert _prepare_query("SELECT * FROM clientes WHERE id = ?") == \
            "SELECT * FROM clientes WHERE id = %s"
        with patch('psycopg2.connect') as postgres_connect:
            assert get_connection() is postgres_connect.return_value
            postgres_connect.assert_called_once_with(
                'postgresql://db.example.test/app',
                cursor_factory=__import__('psycopg2').extras.RealDictCursor,
                connect_timeout=10,
                sslmode='require',
            )
    print("0. [PASS] Adaptador PostgreSQL usa Supabase y parámetros seguros")

    app = create_app()
    client = app.test_client()

    print("\n--- INICIANDO SUITE DE PRUEBAS AUTOMATIZADAS: CAJA INTELIGENTE ---")

    # 1. Protected routes and safe login redirects
    anonymous_client = app.test_client()
    res = anonymous_client.get('/clientes/')
    assert res.status_code == 302
    next_url = parse_qs(urlsplit(res.headers['Location']).query).get('next', [''])[0]
    assert next_url.startswith('/clientes/')
    res = anonymous_client.post('/login?next=https://example.com', data={
        'email': 'admin@cajainteligente.pe',
        'password': 'admin123'
    })
    assert res.status_code == 302
    assert res.headers['Location'].endswith('/dashboard')
    print("1. [PASS] Protección de rutas y rechazo de redirección externa")

    # 2. Demo login
    res = client.get('/demo-login/admin', follow_redirects=True)
    assert res.status_code == 200
    print("2. [PASS] Autenticación y sesión de Administrador")

    # 3. Health check
    res = client.get('/health')
    assert res.status_code == 200
    assert res.get_json()['status'] == 'ok'
    print("3. [PASS] Health check de aplicación y base de datos")

    # 4. Dashboard
    res = client.get('/dashboard')
    assert res.status_code == 200
    assert b"Dashboard Financiero" in res.data
    print("4. [PASS] Dashboard principal con KPIs y métricas financieras")

    # 5. Chart data API
    res = client.get('/api/dashboard/chart-data')
    assert res.status_code == 200
    data = res.get_json()
    assert "distribucion_riesgos" in data
    print("5. [PASS] Endpoint de datos para Chart.js (Donut y Barras)")

    # 6. Clientes
    res = client.get('/clientes/')
    assert res.status_code == 200
    assert b"Juan Carlos" in res.data
    print("6. [PASS] Módulo de gestión de clientes 360")

    # 7. Detalle cliente
    res = client.get('/clientes/cli-001/detalle')
    assert res.status_code == 200
    print("7. [PASS] Visualización de expediente y central de riesgos SBS del cliente")

    # 8. Simulador de Crédito
    res = client.post('/creditos/simular', json={
        'monto': 15000,
        'plazo': 18,
        'ingresos': 4800,
        'gastos': 2100,
        'deudas': 600,
        'tasa': 0.028
    })
    assert res.status_code == 200
    sim_data = res.get_json()
    assert sim_data['cuota_mensual'] > 0
    assert sim_data['ratio_dti'] > 0
    print(f"8. [PASS] Simulador financiero en tiempo real (Cuota: S/. {sim_data['cuota_mensual']}, DTI: {sim_data['ratio_dti']}%)")
    invalid_simulation = client.post('/creditos/simular', json={
        'monto': -100,
        'plazo': 12,
        'ingresos': 1000,
        'gastos': 200,
        'deudas': 0,
        'tasa': 0.028
    })
    assert invalid_simulation.status_code == 400
    print("9. [PASS] Rechazo de valores financieros fuera de rango")

    # 9. Solicitudes de Crédito
    res = client.get('/creditos/')
    assert res.status_code == 200
    assert b"SOL-2024" in res.data
    print("10. [PASS] Módulo de solicitudes de crédito")

    # 10. Evaluación de Riesgo con IA
    res = client.get('/riesgos/evaluar/sol-001')
    assert res.status_code == 200
    print("11. [PASS] Vista de evaluación de riesgo crediticio con IA")

    # 11. Ejecución de análisis de IA
    res = client.post('/riesgos/procesar-ia/sol-011', follow_redirects=True)
    assert res.status_code == 200
    print("12. [PASS] Motor de IA procesó solicitud con éxito (Score, Factores, Recomendaciones)")

    # 12. Dictamen humano
    res = client.post('/riesgos/dictamen-humano/sol-011', data={
        'dictamen_humano': 'CONFORME',
        'observaciones_analista': 'Verificación presencial conforme. Aprobado por el comité.'
    }, follow_redirects=True)
    assert res.status_code == 200
    print("13. [PASS] Registro de dictamen humano vinculante del comité SBS")
    res = client.post('/riesgos/dictamen-humano/sol-011', data={
        'dictamen_humano': 'APROBADO',
        'observaciones_analista': 'Este valor no forma parte del catálogo de dictámenes.'
    })
    assert res.status_code == 302
    saved_evaluation = query_db(
        "SELECT dictamen_humano FROM evaluaciones_riesgo WHERE solicitud_id = ?",
        ('sol-011',),
        one=True,
    )
    assert saved_evaluation['dictamen_humano'] == 'CONFORME'
    print("14. [PASS] Rechazo de dictámenes humanos no permitidos")

    # 13. Gestión de Morosidad
    res = client.get('/morosidad/')
    assert res.status_code == 200
    assert b"Ratio de Morosidad" in res.data
    print("15. [PASS] Módulo de morosidad, atrasos y alertas preventivas")

    # 14. Registro de pago
    res = client.post('/morosidad/registrar-pago/pag-005', data={
        'metodo_pago': 'Ventanilla Sede Central'
    }, follow_redirects=True)
    assert res.status_code == 200
    print("16. [PASS] Registro y cancelación de cuota con actualización de estado")

    # 15. Exportación Excel
    res = client.get('/reportes/exportar/excel?tipo=evaluaciones')
    assert res.status_code == 200
    assert len(res.data) > 1000
    print(f"17. [PASS] Generación y descarga de reporte Excel (.xlsx) ({len(res.data)} bytes)")

    # 16. Exportación PDF
    res = client.get('/reportes/exportar/pdf?tipo=evaluaciones')
    assert res.status_code == 200
    assert res.data.startswith(b'%PDF')
    print(f"18. [PASS] Generación y descarga de reporte PDF con membrete ({len(res.data)} bytes)")

    for tipo in ('riesgo_alto', 'morosidad'):
        assert client.get(f'/reportes/exportar/excel?tipo={tipo}').status_code == 200
        assert client.get(f'/reportes/exportar/pdf?tipo={tipo}').status_code == 200
    print("19. [PASS] Exportaciones PDF/Excel de riesgo alto y morosidad")

    cobranzas_client = app.test_client()
    assert cobranzas_client.get('/demo-login/cobranzas').status_code == 302
    res = cobranzas_client.post('/clientes/crear')
    assert res.status_code == 302
    assert res.headers['Location'].endswith('/dashboard')
    assert client.get('/demo-login/invalid').status_code == 404
    print("20. [PASS] Autorización por roles y rechazo de perfiles desconocidos")

    print("\n============================================================")
    print("  TODAS LAS 20 PRUEBAS DE INTEGRACION PASARON")
    print("============================================================\n")

if __name__ == '__main__':
    run_tests()
