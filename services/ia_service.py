"""
Servicio de Inteligencia Artificial para Evaluación de Riesgo Crediticio
Integración con la API de OpenAI y Motor de Inferencia Heurística de Respaldo (Modo Demo).
Diseñado específicamente para el ecosistema de Cajas Municipales de Ahorro y Crédito (CMAC).
"""

import os
import json
from config import Config
from services.credit_scoring import calcular_scoring_analitico

def analizar_riesgo_con_ia(datos_solicitud: dict, datos_cliente: dict) -> dict:
    """
    Función principal de evaluación con IA.
    Intenta utilizar la API de OpenAI si está configurada;
    de lo contrario o ante fallos, conmuta fluidamente al Motor de IA de Demostración.
    """
    metricas = calcular_scoring_analitico({**datos_cliente, **datos_solicitud})
    
    # Si hay clave de OpenAI configurada y no es un valor placeholder
    if Config.OPENAI_API_KEY and not Config.OPENAI_API_KEY.startswith("sk-tu-api-key"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=Config.OPENAI_API_KEY)
            
            prompt_sistema = """Eres un Oficial Senior de Riesgos Crediticios y Científico de Datos especialista en Microfinanzas y Cajas Municipales de Ahorro y Crédito del Perú (SBS).
Tu rol es asistir a los comités y analistas de crédito analizando solicitudes financieras de manera ética, explicativa y técnica.

REGLAS ESTRICTAS:
1. No tomes decisiones finales vinculantes: genera evaluaciones como recomendación explicativa para el analista humano.
2. No discrimines por género, raza, religión o factores protegidos. Basa tu análisis exclusivamente en capacidad de pago, flujo de caja, endeudamiento (DTI) y comportamiento histórico.
3. Clasifica el riesgo en: 'BAJO', 'MEDIO' o 'ALTO'.
4. Devuelve ÚNICAMENTE un objeto JSON válido con la siguiente estructura:
{
  "score_riesgo": <entero entre 0 y 100>,
  "nivel_riesgo": "BAJO" | "MEDIO" | "ALTO",
  "resumen_evaluacion": "<texto explicativo detallado de 2 a 3 párrafos técnicos>",
  "factores_positivos": ["<fortaleza 1>", "<fortaleza 2>", "<fortaleza 3>"],
  "factores_negativos": ["<debilidad 1>", "<debilidad 2>"],
  "senales_alerta": ["<alerta preventiva temprana 1>", "<alerta 2>"],
  "probabilidad_morosidad_30d": <flotante porcentaje, ej 5.5>,
  "probabilidad_morosidad_90d": <flotante porcentaje, ej 12.0>,
  "recomendaciones": "<recomendaciones prácticas para el analista: aprobación condicionada, garantías, plazo, monto>"
}"""

            prompt_usuario = f"""Evalúa la siguiente solicitud de crédito para Caja Inteligente:
DATOS DEL CLIENTE:
- Nombre: {datos_cliente.get('nombres')} {datos_cliente.get('apellidos')}
- DNI: {datos_cliente.get('dni')}
- Edad: {datos_cliente.get('edad')} años
- Ocupación: {datos_cliente.get('ocupacion')}
- Sector: {datos_cliente.get('sector_economico', 'Comercio')}
- Situación Laboral: {datos_solicitud.get('situacion_laboral')}

MÉTRICAS FINANCIERAS CUANTITATIVAS CALCULADAS:
- Ingresos Mensuales: S/. {metricas.get('ingresos', datos_solicitud.get('ingresos_declarados'))}
- Gastos Mensuales: S/. {metricas.get('gastos', datos_solicitud.get('gastos_declarados'))}
- Deudas Actuales en Sistema: S/. {metricas.get('deudas', datos_solicitud.get('deudas_declaradas'))}
- Monto Solicitado: S/. {datos_solicitud.get('monto_solicitado')} a {datos_solicitud.get('plazo_meses')} meses
- Tipo de Crédito: {datos_solicitud.get('tipo_credito')}
- Cuota Mensual Estimada: S/. {metricas.get('cuota_estimada')}
- Ratio Deuda/Ingreso (DTI): {metricas.get('ratio_dti')}%
- Capacidad de Pago Mensual: S/. {metricas.get('capacidad_pago')}
- Ingreso Disponible Neto (después de cuota): S/. {metricas.get('ingreso_disponible')}
- Historial Crediticio SBS Reportado: {datos_solicitud.get('historial_pagos')}
- Score Preliminar Cuantitativo: {metricas.get('score_riesgo')} / 100"""

            response = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": prompt_usuario}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )

            contenido = response.choices[0].message.content
            resultado_ia = json.loads(contenido)
            
            # Validar y agregar metadatos
            resultado_ia["modelo_ia_utilizado"] = f"OpenAI {Config.OPENAI_MODEL}"
            resultado_ia["es_modo_demo"] = False
            resultado_ia["aviso_legal"] = "Evaluación generada por IA (OpenAI) como herramienta de apoyo analítico. La decisión final corresponde al comité de créditos humano conforme a normas SBS."
            return resultado_ia

        except Exception as err:
            print(f"[WARN] Error invocando OpenAI API ({err}). Activando Motor IA Demostración...")
            return generar_evaluacion_heuristica_ia(datos_solicitud, datos_cliente, metricas, motivo="Fallback por excepción en API")

    # Si no hay clave, ejecutar el motor de demostración
    return generar_evaluacion_heuristica_ia(datos_solicitud, datos_cliente, metricas, motivo="Modo Demostración Activo")

def generar_evaluacion_heuristica_ia(solicitud: dict, cliente: dict, metricas: dict, motivo: str = "") -> dict:
    """
    Motor Heurístico de IA Explicable para Demostración.
    Genera un dictamen cualitativo y cuantitativo idéntico en estructura y profundidad técnica
    al proporcionado por OpenAI, permitiendo que la plataforma funcione al 100% sin dependencias externas.
    """
    score = metricas["score_riesgo"]
    nivel = metricas["nivel_riesgo"]
    dti = metricas["ratio_dti"]
    disponible = metricas["ingreso_disponible"]
    cuota = metricas["cuota_estimada"]
    historial = solicitud.get("historial_pagos", "Puntual sin atrasos")
    ocupacion = cliente.get("ocupacion", "Microempresario")
    nombre = f"{cliente.get('nombres', '')} {cliente.get('apellidos', '')}".strip()
    monto = float(solicitud.get("monto_solicitado", 0))

    factores_positivos = []
    factores_negativos = []
    senales_alerta = []

    # Construcción de factores y evaluación
    if dti <= 35.0:
        factores_positivos.append(f"Ratio Deuda/Ingresos (DTI) sumamente saludable de {dti}%, inferior al umbral prudencial del 35%.")
    elif dti <= 50.0:
        factores_positivos.append(f"Endeudamiento moderado ({dti}%) dentro de parámetros tolerables para crédito productivo.")
        factores_negativos.append(f"Ratio DTI de {dti}% se acerca al límite máximo de endeudamiento permitido.")
    else:
        factores_negativos.append(f"Sobreendeudamiento crítico: DTI de {dti}% excede el límite del 50%, comprometiendo la liquidez.")
        senales_alerta.append(f"ALERTA ROJA: El cliente compromete más del 50% de sus ingresos totales en amortización de pasivos.")

    if disponible > 0:
        factores_positivos.append(f"Flujo de caja superavitario: Genera S/. {disponible:,.2f} de ingreso libre mensual tras atender la cuota proyectada.")
    else:
        factores_negativos.append(f"Flujo de caja proyectado deficitario (-S/. {abs(disponible):,.2f}). La cuota supera el excedente real.")
        senales_alerta.append("Déficit de cobertura de cuota: Alto riesgo de iliquidez operativa en los primeros 60 días.")

    if "Puntual" in historial:
        factores_positivos.append("Excelente cultura de pago histórica en el sistema financiero regulado por la SBS.")
    elif "Atrasos leves" in historial:
        factores_negativos.append("Presenta historial con atrasos esporádicos de 1 a 8 días en compromisos pasados.")
        senales_alerta.append("Tendencia a mora temprana: Se sugiere calendarizar fechas de pago coincidentes con cobros de clientes.")
    else:
        factores_negativos.append("Antecedentes de morosidad regularizada o calificación CPP en centrales de riesgo.")
        senales_alerta.append("Historial crediticio con antecedentes de incumplimiento en el último periodo anual.")

    if "formal" in solicitud.get("situacion_laboral", "").lower():
        factores_positivos.append("Estabilidad laboral formal verificable con sustento documentario de flujos.")
    else:
        factores_negativos.append("Actividad en sector informal con variabilidad estacional en ingresos declarados.")
        senales_alerta.append("Requerir inspección in-situ del negocio para validar volumen físico de ventas.")

    # Generación de Resumen y Recomendaciones según nivel
    if nivel == "BAJO":
        prob_30d = round(2.0 + (100 - score) * 0.1, 1)
        prob_90d = round(3.5 + (100 - score) * 0.15, 1)
        resumen = (
            f"Evaluación crediticia favorable para {nombre}. El solicitante exhibe un perfil financiero de alta solidez, "
            f"con una capacidad de cobertura holgada sobre la cuota mensual de S/. {cuota:,.2f}. Su ratio DTI del {dti}% "
            f"garantiza un margen operativo seguro para el desarrollo de su actividad ({ocupacion}). Se califica con score de {score}/100 "
            f"dentro de los rangos de riesgo mínimo exigidos por las políticas de colocación de la Caja Municipal."
        )
        recomendaciones = (
            f"1. APROBACIÓN RECOMENDADA por el monto total de S/. {monto:,.2f}.\n"
            f"2. Establecer desembolso con retención de primera cuota o débito automático en cuenta de ahorro.\n"
            f"3. Ofrecer tasa preferencial de fidelización por excelente historial crediticio."
        )
    elif nivel == "MEDIO":
        prob_30d = round(15.0 + (75 - score) * 0.4, 1)
        prob_90d = round(28.0 + (75 - score) * 0.5, 1)
        resumen = (
            f"Evaluación crediticia con advertencias para {nombre}. Si bien la actividad económica ({ocupacion}) genera flujos, "
            f"el ratio de endeudamiento DTI del {dti}% y los compromisos vigentes restringen el margen de maniobra ante imprevistos. "
            f"El score crediticio de {score}/100 amerita una revisión exhaustiva de garantías y verificación de pasivos no declarados."
        )
        recomendaciones = (
            f"1. RECOMENDACIÓN CONDICIONADA: Requerir aval solidario con ingresos demostrables de 5ta categoría o garantía mobiliaria.\n"
            f"2. Sugerir ajuste de monto a S/. {monto * 0.8:,.2f} o extender el plazo para reducir la cuota mensual a menos de S/. {cuota * 0.75:,.2f}.\n"
            f"3. Monitoreo mensual de cumplimiento con alertas de mora temprana a partir del día 3 de vencimiento."
        )
    else:
        prob_30d = round(45.0 + (50 - score) * 0.7, 1)
        prob_90d = round(65.0 + (50 - score) * 0.6, 1)
        resumen = (
            f"ALTO RIESGO DE MOROSIDAD detectado para {nombre}. El perfil financiero actual evidencia insuficiencia en la capacidad de pago "
            f"y un sobreendeudamiento marcado (DTI: {dti}%). La cuota proyectada de S/. {cuota:,.2f} genera un descalce de liquidez "
            f"inmediato que llevaría a mora en el corto plazo. El score de {score}/100 no alcanza los umbrales mínimos de colocación prudente."
        )
        recomendaciones = (
            f"1. DESESTIMAR SOLICITUD EN CONDICIONES ACTUALES para evitar sobreendeudar al solicitante.\n"
            f"2. Ofrecer programa de asesoría financiera o consolidación de deudas preexistentes a menor tasa.\n"
            f"3. En caso excepcional de reconsideración, exigir garantía hipotecaria inscrita en SUNARP con cobertura mayor al 150% del préstamo."
        )

    return {
        "score_riesgo": score,
        "nivel_riesgo": nivel,
        "resumen_evaluacion": resumen,
        "factores_positivos": factores_positivos,
        "factores_negativos": factores_negativos,
        "senales_alerta": senales_alerta,
        "probabilidad_morosidad_30d": min(95.0, prob_30d),
        "probabilidad_morosidad_90d": min(98.0, prob_90d),
        "recomendaciones": recomendaciones,
        "modelo_ia_utilizado": "CajaIA-Engine (Heurística Microfinanciera SBS)",
        "es_modo_demo": True,
        "aviso_legal": "Evaluación asistida por Inteligencia Artificial orientada a la toma de decisión humana. Cumple con la normativa de gestión de riesgo crediticio SBS Resolución N° 11356-2008."
    }
