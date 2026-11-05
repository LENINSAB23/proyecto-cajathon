"""
Servicio de Scoring Crediticio y Modelos Financieros CMAC / SBS Perú
Implementa fórmulas financieras de capacidad de pago, cuota francesa,
ratio Deuda/Ingresos (DTI) y clasificación de riesgo crediticio.
"""

def calcular_cuota_mensual(monto: float, plazo_meses: int, tasa_mensual: float = 0.028) -> float:
    """
    Calcula la cuota mensual fija usando el sistema de amortización francés.
    Fórmula: C = P * [ i * (1+i)^n ] / [ (1+i)^n - 1 ]
    """
    if plazo_meses <= 0 or monto <= 0:
        return 0.0
    if tasa_mensual <= 0:
        return round(monto / plazo_meses, 2)
    
    i = tasa_mensual
    n = plazo_meses
    factor = (1 + i) ** n
    cuota = monto * (i * factor) / (factor - 1)
    return round(float(cuota), 2)

def calcular_capacidad_pago(ingresos: float, gastos: float, factor_seguridad: float = 0.85) -> float:
    """
    Calcula la capacidad de pago admisible del cliente considerando un factor
    de seguridad para gastos imprevistos.
    Capacidad = (Ingresos - Gastos) * factor_seguridad
    """
    excedente = max(0.0, float(ingresos) - float(gastos))
    return round(excedente * factor_seguridad, 2)

def calcular_ratio_dti(deudas_actuales: float, cuota_estimada: float, ingresos: float) -> float:
    """
    Debt-to-Income Ratio (DTI) o Ratio de Endeudamiento Total.
    DTI = ((Deudas Actuales + Cuota Estimada) / Ingresos) * 100
    """
    if ingresos <= 0:
        return 100.0
    compromiso_total = float(deudas_actuales) + float(cuota_estimada)
    dti = (compromiso_total / float(ingresos)) * 100.0
    return round(float(dti), 2)

def calcular_ingreso_disponible(ingresos: float, gastos: float, deudas_actuales: float, cuota_estimada: float) -> float:
    """
    Calcula el flujo libre remanente luego de cubrir gastos personales/negocio,
    deudas financieras preexistentes y la nueva cuota proyectada.
    """
    disponible = float(ingresos) - float(gastos) - float(deudas_actuales) - float(cuota_estimada)
    return round(float(disponible), 2)

def clasificar_dias_mora_sbs(dias_atraso: int) -> dict:
    """
    Clasificación crediticia de la Superintendencia de Banca, Seguros y AFP (SBS) del Perú:
    - Normal (0): 0 a 8 días de atraso
    - Con Problemas Potenciales CPP (1): 9 a 30 días
    - Deficiente (2): 31 a 60 días
    - Dudoso (3): 61 a 120 días
    - Pérdida (4): más de 120 días
    """
    if dias_atraso <= 8:
        return {
            "categoria": "Normal (0 días)",
            "codigo": 0,
            "nivel": "BAJO",
            "clase_badge": "badge-success",
            "provision_requerida": "1.0%"
        }
    elif dias_atraso <= 30:
        return {
            "categoria": "Con Problemas Potenciales CPP (9-30 días)",
            "codigo": 1,
            "nivel": "MEDIO",
            "clase_badge": "badge-warning",
            "provision_requerida": "5.0%"
        }
    elif dias_atraso <= 60:
        return {
            "categoria": "Deficiente (31-60 días)",
            "codigo": 2,
            "nivel": "ALTO",
            "clase_badge": "badge-danger",
            "provision_requerida": "20.0%"
        }
    elif dias_atraso <= 120:
        return {
            "categoria": "Dudoso (61-120 días)",
            "codigo": 3,
            "nivel": "ALTO",
            "clase_badge": "badge-danger",
            "provision_requerida": "60.0%"
        }
    else:
        return {
            "categoria": "Pérdida (>120 días)",
            "codigo": 4,
            "nivel": "CRITICO",
            "clase_badge": "badge-dark",
            "provision_requerida": "100.0%"
        }

def calcular_scoring_analitico(datos: dict) -> dict:
    """
    Motor analítico cuantitativo ponderado para microfinanzas:
    Evalúa variables cuantitativas y cualitativas conforme a estándares de CMACs.
    """
    ingresos = float(datos.get("ingresos_declarados", datos.get("ingresos_mensuales", 0)))
    gastos = float(datos.get("gastos_declarados", datos.get("gastos_mensuales", 0)))
    deudas = float(datos.get("deudas_declaradas", datos.get("deudas_actuales", 0)))
    monto = float(datos.get("monto_solicitado", 0))
    plazo = int(datos.get("plazo_meses", 12))
    historial = str(datos.get("historial_pagos", "Puntual sin atrasos"))
    laboral = str(datos.get("situacion_laboral", "Microempresario / Negocio propio"))
    tasa = float(datos.get("tasa_interes_mensual", 0.028))

    cuota = calcular_cuota_mensual(monto, plazo, tasa)
    dti = calcular_ratio_dti(deudas, cuota, ingresos)
    capacidad = calcular_capacidad_pago(ingresos, gastos)
    disponible = calcular_ingreso_disponible(ingresos, gastos, deudas, cuota)

    # Puntuación base sobre 100 puntos:
    # 1. Componente DTI (máx 35 pts)
    if dti <= 30.0:
        pts_dti = 35
    elif dti <= 40.0:
        pts_dti = 28
    elif dti <= 50.0:
        pts_dti = 18
    elif dti <= 60.0:
        pts_dti = 8
    else:
        pts_dti = 0

    # 2. Componente Cobertura de Cuota (máx 25 pts)
    excedente_neto = max(0.0, ingresos - gastos - deudas)
    cobertura = (excedente_neto / cuota) if cuota > 0 else 0
    if cobertura >= 2.0:
        pts_cobertura = 25
    elif cobertura >= 1.5:
        pts_cobertura = 20
    elif cobertura >= 1.2:
        pts_cobertura = 14
    elif cobertura >= 1.0:
        pts_cobertura = 8
    else:
        pts_cobertura = 0

    # 3. Componente Historial Crediticio (máx 25 pts)
    if "Puntual" in historial:
        pts_historial = 25
    elif "Atrasos leves" in historial:
        pts_historial = 15
    elif "nuevo" in historial.lower():
        pts_historial = 12
    else:  # Morosidad previa
        pts_historial = 4

    # 4. Componente Estabilidad Laboral y Sector (máx 15 pts)
    if "formal" in laboral.lower() or "dependiente" in laboral.lower():
        pts_laboral = 15
    elif "microempresario" in laboral.lower():
        pts_laboral = 12
    else:  # informal
        pts_laboral = 6

    score = pts_dti + pts_cobertura + pts_historial + pts_laboral
    score = max(5, min(98, score))

    # Determinación de Nivel de Riesgo
    if score >= 75 and dti <= 42.0 and disponible > 0:
        nivel_riesgo = "BAJO"
    elif score >= 50 and dti <= 55.0 and disponible >= -200:
        nivel_riesgo = "MEDIO"
    else:
        nivel_riesgo = "ALTO"

    return {
        "score_riesgo": score,
        "nivel_riesgo": nivel_riesgo,
        "cuota_estimada": cuota,
        "ratio_dti": dti,
        "capacidad_pago": capacidad,
        "ingreso_disponible": disponible,
        "cobertura_cuota": round(cobertura, 2),
        "pts_dti": pts_dti,
        "pts_cobertura": pts_cobertura,
        "pts_historial": pts_historial,
        "pts_laboral": pts_laboral
    }
