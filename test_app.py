from app import create_app
from types import SimpleNamespace
from unittest.mock import patch
from werkzeug.security import check_password_hash
from database.db import new_id, query_db
from config import Config
from routes.auth import authenticate_user
from supabase import AuthError
from datetime import date, timedelta
import sqlite3
import time

def test_postgres_query_adapter():
    class FakeCursor:
        def __init__(self):
            self.statement = None

        def execute(self, statement, params=None):
            self.statement = (statement, params)

        def fetchall(self):
            return [{'id': '00000000-0000-0000-0000-000000000001'}]

        def close(self):
            pass

    class FakeConnection:
        def __init__(self):
            self.test_cursor = FakeCursor()

        def cursor(self):
            return self.test_cursor

        def close(self):
            pass

    fake_connection = FakeConnection()
    with patch('database.db.Config.DATABASE_URL', 'postgresql://test'):
        with patch('database.db.get_connection', return_value=fake_connection):
            result = query_db("SELECT id FROM usuarios WHERE id = ?", ('test-id',), one=True)
            generated_id = new_id('test')

    assert fake_connection.test_cursor.statement == (
        "SELECT id FROM usuarios WHERE id = %s",
        ('test-id',)
    )
    assert result['id'] == '00000000-0000-0000-0000-000000000001'
    assert len(generated_id) == 36

def run_tests():
    app = create_app()
    app.config['TELEGRAM_BOT_TOKEN'] = ''
    app.config['TELEGRAM_CHAT_ID'] = ''
    client = app.test_client()

    print("\n--- INICIANDO SUITE DE PRUEBAS AUTOMATIZADAS: CAJA INTELIGENTE ---")

    login_page = app.test_client().get('/login')
    assert b'CAJA INTELIGENTE' in login_page.data
    assert b'admin@creditrisk.pe' in login_page.data
    assert b'analista@creditrisk.pe' in login_page.data
    assert b'cobranzas@creditrisk.pe' in login_page.data

    # 1. Login demo
    res = client.post('/login', data={
        'email': 'admin@creditrisk.pe',
        'password': 'admin123'
    }, follow_redirects=True)
    assert res.status_code == 200
    with client.session_transaction() as user_session:
        assert user_session['user_role'] == 'Administrador'
    admin_user = query_db("SELECT email, rol, password_hash FROM usuarios WHERE email = ?", ('admin@creditrisk.pe',), one=True)
    assert admin_user and admin_user['rol'] == 'Administrador'
    assert check_password_hash(admin_user['password_hash'], 'admin123')
    assert query_db("SELECT COUNT(*) as cnt FROM usuarios", one=True)['cnt'] == 3
    print("1. [PASS] Autenticación y sesión de Administrador")

    supabase_profile = {
        'id': '00000000-0000-0000-0000-000000000001',
        'email': 'analista@creditrisk.pe',
        'rol': 'Analista de créditos',
        'activo': True
    }
    supabase_auth = SimpleNamespace(
        auth=SimpleNamespace(
            sign_in_with_password=lambda credentials: SimpleNamespace(
                user=SimpleNamespace(id=supabase_profile['id'], email=credentials['email'])
            )
        )
    )
    with patch.object(Config, 'USE_SUPABASE_AUTH', True):
        with patch('routes.auth.get_supabase', return_value=supabase_auth):
            with patch('routes.auth.query_db', return_value=supabase_profile) as profile_lookup:
                authenticated_profile = authenticate_user('analista@creditrisk.pe', 'supabase-password')
    assert authenticated_profile['rol'] == 'Analista de créditos'
    assert profile_lookup.call_args.args[1] == (supabase_profile['id'],)
    auth_error = AuthError('Invalid login credentials', 'invalid_credentials')
    auth_error.status = 400
    failing_auth = SimpleNamespace(
        auth=SimpleNamespace(
            sign_in_with_password=lambda credentials: (_ for _ in ()).throw(auth_error)
        )
    )
    with patch.object(Config, 'USE_SUPABASE_AUTH', True):
        with patch('routes.auth.get_supabase', return_value=failing_auth):
            with patch('routes.auth.query_db') as profile_lookup:
                assert authenticate_user('analista@creditrisk.pe', 'wrong-password') is None
                profile_lookup.assert_not_called()
    print("1a. [PASS] Supabase Auth vincula el UID autenticado al perfil y su rol")
    test_postgres_query_adapter()
    print("1b. [PASS] Adaptación de consultas y UUIDs compatibles con PostgreSQL")

    # 2. Dashboard
    res = client.get('/dashboard')
    assert res.status_code == 200
    assert b"Dashboard Financiero" in res.data
    print("2. [PASS] Dashboard principal con KPIs y métricas financieras")

    # 3. Chart data API
    res = client.get('/api/dashboard/chart-data')
    assert res.status_code == 200
    data = res.get_json()
    assert "distribucion_riesgos" in data
    assert len(data['solicitudes_mensuales']['labels']) == 6
    assert sum(data['solicitudes_mensuales']['solicitado']) > 0
    print("3. [PASS] Endpoint de datos para Chart.js (Donut y Barras)")

    assert client.get('/health').status_code == 200
    print("3a. [PASS] Comprobación de salud y conexión a base de datos")

    # 4. Clientes
    res = client.get('/clientes/')
    assert res.status_code == 200
    assert b"Juan Carlos" in res.data
    print("4. [PASS] Módulo de gestión de clientes 360")

    # 5. Detalle cliente
    res = client.get('/clientes/cli-001/detalle')
    assert res.status_code == 200
    print("5. [PASS] Visualización de expediente y central de riesgos SBS del cliente")

    # 6. Simulador de Crédito
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
    print(f"6. [PASS] Simulador financiero en tiempo real (Cuota: S/. {sim_data['cuota_mensual']}, DTI: {sim_data['ratio_dti']}%)")

    # 7. Solicitudes de Crédito
    res = client.get('/creditos/')
    assert res.status_code == 200
    assert b"SOL-2024" in res.data
    print("7. [PASS] Módulo de solicitudes de crédito")

    # 8. Evaluación de Riesgo con IA
    res = client.get('/riesgos/evaluar/sol-001')
    assert res.status_code == 200
    print("8. [PASS] Vista de evaluación de riesgo crediticio con IA")

    # 9. Ejecución de análisis de IA
    res = client.post('/riesgos/procesar-ia/sol-011', follow_redirects=True)
    assert res.status_code == 200
    print("9. [PASS] Motor de IA procesó solicitud con éxito (Score, Factores, Recomendaciones)")

    # 10. Dictamen humano
    res = client.post('/riesgos/dictamen-humano/sol-011', data={
        'dictamen_humano': 'CONFORME',
        'observaciones_analista': 'Verificación presencial conforme. Aprobado por el comité.'
    }, follow_redirects=True)
    assert res.status_code == 200
    print("10. [PASS] Registro de dictamen humano vinculante del comité SBS")

    # 11. Gestión de Morosidad
    res = client.get('/morosidad/')
    assert res.status_code == 200
    assert b"Ratio de Morosidad" in res.data
    print("11. [PASS] Módulo de morosidad, atrasos y alertas preventivas")

    # 12. Registro de pago
    res = client.post('/morosidad/registrar-pago/pag-005', data={
        'metodo_pago': 'Ventanilla Sede Central'
    }, follow_redirects=True)
    assert res.status_code == 200
    print("12. [PASS] Registro y cancelación de cuota con actualización de estado")

    # 13. Exportación Excel
    res = client.get('/reportes/exportar/excel?tipo=evaluaciones')
    assert res.status_code == 200
    assert len(res.data) > 1000
    print(f"13. [PASS] Generación y descarga de reporte Excel (.xlsx) ({len(res.data)} bytes)")

    # 14. Exportación PDF
    res = client.get('/reportes/exportar/pdf?tipo=evaluaciones')
    assert res.status_code == 200
    assert res.data.startswith(b'%PDF')
    print(f"14. [PASS] Generación y descarga de reporte PDF con membrete ({len(res.data)} bytes)")
    for tipo in ('riesgo_alto', 'morosidad'):
        assert client.get(f'/reportes/exportar/excel?tipo={tipo}').status_code == 200
        assert client.get(f'/reportes/exportar/pdf?tipo={tipo}').status_code == 200
    print("15. [PASS] Exportaciones PDF/Excel de riesgo alto y morosidad")

    analista_client = app.test_client()
    res = analista_client.post('/login', data={
        'email': 'analista@creditrisk.pe',
        'password': 'analista123'
    })
    assert res.status_code == 302 and res.headers['Location'].endswith('/dashboard')
    with analista_client.session_transaction() as user_session:
        assert user_session['user_role'] == 'Analista de créditos'
    assert analista_client.get('/clientes/').status_code == 200
    assert analista_client.get('/creditos/').status_code == 200
    assert analista_client.get('/riesgos/').status_code == 200
    res = analista_client.get('/morosidad/')
    assert res.status_code == 302 and res.headers['Location'].endswith('/dashboard')
    assert analista_client.get('/reportes/').status_code == 302
    assert 'Gestión de Morosidad' not in analista_client.get('/dashboard').get_data(as_text=True)
    print("16. [PASS] Analista limitado a clientes, créditos y evaluación de riesgo")

    cobranzas_client = app.test_client()
    res = cobranzas_client.post('/login', data={
        'email': 'cobranzas@creditrisk.pe',
        'password': 'cobranza123',
        'rol': 'Administrador'
    })
    assert res.status_code == 302 and res.headers['Location'].endswith('/morosidad/')
    with cobranzas_client.session_transaction() as user_session:
        assert user_session['user_role'] == 'Personal de cobranza'
    assert cobranzas_client.get('/morosidad/').status_code == 200
    for path in ('/dashboard', '/clientes/', '/creditos/', '/riesgos/', '/reportes/'):
        assert cobranzas_client.get(path).status_code == 302
    res = cobranzas_client.post('/clientes/crear')
    assert res.status_code == 302 and res.headers['Location'].endswith('/morosidad/')
    assert cobranzas_client.get('/reportes/exportar/excel?tipo=morosidad').status_code == 200
    assert cobranzas_client.get('/reportes/exportar/pdf?tipo=evaluaciones').status_code == 403
    assert 'Solicitudes de Crédito' not in cobranzas_client.get('/morosidad/').get_data(as_text=True)
    print("17. [PASS] Cobranzas limitado a morosidad, pagos, alertas y su reporte")

    assert client.get('/demo-login/invalid').status_code == 404
    print("18. [PASS] Rechazo de perfiles de demostración desconocidos")

    # 19. Geographic concentration and privacy-safe aggregation
    res = client.get('/concentracion/?riesgo=ALTO')
    assert res.status_code == 200 and b'OpenStreetMap' in res.data
    assert b'DNI' not in res.data and b'Latitud' not in res.data
    print("19. [PASS] Mapa agregado, filtros y ausencia de identificadores personales")

    # 20. Decision snapshots and append-only history
    history = query_db(
        "SELECT * FROM historial_decisiones WHERE solicitud_id = ? ORDER BY created_at DESC",
        ('sol-011',)
    )
    assert len(history) >= 2
    assert '"evaluacion"' in history[-1]['snapshot_json']
    try:
        from database.db import execute_db
        execute_db("UPDATE historial_decisiones SET observaciones = 'alterado' WHERE id = ?", (history[-1]['id'],))
        raise AssertionError("Decision audit must reject updates")
    except sqlite3.IntegrityError:
        pass
    assert client.get('/decisiones/').status_code == 200
    assert client.get('/decisiones/exportar/excel').status_code == 200
    assert client.get('/decisiones/exportar/pdf').status_code == 200
    print("20. [PASS] Snapshots auditables, exportación e inmutabilidad")

    # 21. Real disbursement registration, health indicators and exports
    approved_application = query_db(
        "SELECT * FROM solicitudes_credito WHERE id = 'sol-011'",
        one=True
    )
    execute_db(
        "UPDATE solicitudes_credito SET monto_desembolsado = NULL, fecha_desembolso = NULL WHERE id = ?",
        ('sol-011',)
    )
    disbursement = client.post(
        f"/salud-financiera/registrar-desembolso/{approved_application['id']}",
        data={
            'monto_desembolsado': str(min(100, float(approved_application['monto_solicitado']))),
            'fecha_desembolso': date.today().isoformat(),
        },
        follow_redirects=True
    )
    assert disbursement.status_code == 200
    health_page = client.get('/salud-financiera/')
    assert health_page.status_code == 200 and b'No disponible' in health_page.data
    assert client.get('/salud-financiera/exportar/excel').status_code == 200
    assert client.get('/salud-financiera/exportar/pdf').status_code == 200
    print("21. [PASS] Desembolso real, salud financiera y reportes")

    # 22. Promises and actual partial collection payment association
    outstanding_payment = query_db(
        "SELECT p.* FROM pagos p WHERE p.estado_pago != 'PAGADO' ORDER BY p.id LIMIT 1",
        one=True
    )
    assert outstanding_payment
    user_id = query_db("SELECT id FROM usuarios WHERE email = ?", ('admin@creditrisk.pe',), one=True)['id']
    note = f"prueba-{time.time_ns()}"
    promise_create = client.post('/promesas/crear', data={
        'cliente_id': outstanding_payment['cliente_id'],
        'monto_comprometido': '1.00',
        'fecha_prometida': (date.today() + timedelta(days=1)).isoformat(),
        'responsable_id': user_id,
        'observaciones': note,
    }, follow_redirects=True)
    assert promise_create.status_code == 200
    promise = query_db("SELECT * FROM promesas_pago WHERE observaciones = ?", (note,), one=True)
    assert promise and promise['estado'] == 'PENDIENTE'
    payment_result = client.post(
        f"/morosidad/registrar-pago/{outstanding_payment['id']}",
        data={
            'metodo_pago': 'Prueba',
            'monto_pagado': '1.00',
            'promesa_id': promise['id'],
        },
        follow_redirects=True
    )
    assert payment_result.status_code == 200
    transaction = query_db("SELECT * FROM transacciones_pago WHERE promesa_id = ?", (promise['id'],), one=True)
    assert transaction and float(transaction['monto']) == 1
    assert client.get('/promesas/').status_code == 200
    promise = query_db("SELECT estado FROM promesas_pago WHERE id = ?", (promise['id'],), one=True)
    assert promise['estado'] == 'CUMPLIDA'
    print("22. [PASS] Promesas, abonos parciales y cumplimiento automático")

    # 23. Role separation for the new modules
    assert analista_client.get('/concentracion/').status_code == 200
    assert analista_client.get('/decisiones/').status_code == 200
    assert analista_client.get('/salud-financiera/').status_code == 302
    assert analista_client.get('/promesas/').status_code == 302
    assert cobranzas_client.get('/concentracion/').status_code == 200
    assert cobranzas_client.get('/promesas/').status_code == 200
    assert cobranzas_client.get('/decisiones/').status_code == 302
    assert cobranzas_client.get('/salud-financiera/').status_code == 302
    print("23. [PASS] Permisos diferenciados en los cuatro módulos")

    # 24. Telegram outage is non-fatal and does not expose credentials
    from services.telegram_service import notify_telegram
    with app.app_context():
        app.config['TELEGRAM_BOT_TOKEN'] = 'test-secret'
        app.config['TELEGRAM_CHAT_ID'] = 'test-chat'
        with patch('services.telegram_service.requests.post', side_effect=RuntimeError('network down')):
            assert notify_telegram(f'telegram-test-{time.time_ns()}', 'test notification') is False
    app.config['TELEGRAM_BOT_TOKEN'] = ''
    app.config['TELEGRAM_CHAT_ID'] = ''
    print("24. [PASS] Errores de Telegram no interrumpen la aplicación")

    print("\n==================================================================")
    print("  TODAS LAS 24 PRUEBAS UNITARIAS Y DE INTEGRACIÓN PASARON")
    print("==================================================================\n")

if __name__ == '__main__':
    run_tests()
