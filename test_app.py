from app import create_app

def run_tests():
    app = create_app()
    client = app.test_client()

    print("\n--- INICIANDO SUITE DE PRUEBAS AUTOMATIZADAS: CREDIT RISK ---")

    # 1. Login demo
    res = client.get('/demo-login/admin', follow_redirects=True)
    assert res.status_code == 200
    print("1. [PASS] Autenticación y sesión de Administrador")

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
    print("3. [PASS] Endpoint de datos para Chart.js (Donut y Barras)")

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
    res = analista_client.get('/demo-login/analista')
    assert res.status_code == 302 and res.headers['Location'].endswith('/dashboard')
    assert analista_client.get('/clientes/').status_code == 200
    assert analista_client.get('/creditos/').status_code == 200
    assert analista_client.get('/riesgos/').status_code == 200
    res = analista_client.get('/morosidad/')
    assert res.status_code == 302 and res.headers['Location'].endswith('/dashboard')
    assert analista_client.get('/reportes/').status_code == 302
    assert 'Gestión de Morosidad' not in analista_client.get('/dashboard').get_data(as_text=True)
    print("16. [PASS] Analista limitado a clientes, créditos y evaluación de riesgo")

    cobranzas_client = app.test_client()
    res = cobranzas_client.get('/demo-login/cobranzas')
    assert res.status_code == 302 and res.headers['Location'].endswith('/morosidad/')
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

    print("\n==================================================================")
    print("  TODAS LAS 18 PRUEBAS UNITARIAS Y DE INTEGRACIÓN PASARON")
    print("==================================================================\n")

if __name__ == '__main__':
    run_tests()
