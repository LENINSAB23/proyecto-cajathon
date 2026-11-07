"""
Servicio de Inteligencia Artificial para Evaluación de Riesgo Crediticio - Bank-ito AI
Integración con Google Gemini API, OpenAI y Motor de Inferencia Heurística SBS (Respaldo).
Diseñado específicamente para el ecosistema de Cajas Municipales de Ahorro y Crédito (CMAC).
"""

import os
import json
import requests
from config import Config
from services.credit_scoring import calcular_scoring_analitico

def analizar_riesgo_con_ia(datos_solicitud: dict, datos_cliente: dict) -> dict:
    """
    Función principal de evaluación con IA asistida por Bank-ito.
    1. Intenta evaluar utilizando Google Gemini API (Bank-ito).
    2. Si falla o no está disponible, intenta OpenAI.
    3. Conmuta fluidamente al Motor Heurístico Experto SBS de Bank-ito.
    """
    metricas = calcular_scoring_analitico({**datos_cliente, **datos_solicitud})
    
    prompt_sistema = """Eres Bank-ito, el Oficial Senior de Inteligencia Financiera y Asesor Experto en Riesgo Crediticio para Cajas Municipales de Ahorro y Crédito (CMAC) del Perú reguladas por la SBS.
Tu rol es asistir a los comités y analistas de crédito analizando solicitudes financieras de manera ética, técnica, explicativa y prudencial.

REGLAS ESTRICTAS:
1. No tomes decisiones finales vinculantes: genera evaluaciones como recomendación explicativa para el analista humano según normativa SBS.
2. No discrimines por género, raza, religión o factores protegidos. Basa tu análisis exclusivamente en capacidad de pago, flujo de caja libre, ratio deuda/ingreso (DTI) y comportamiento histórico.
3. Clasifica el riesgo en: 'BAJO', 'MEDIO' o 'ALTO'.
4. Devuelve ÚNICAMENTE un objeto JSON válido con la siguiente estructura:
{
  "score_riesgo": <entero entre 0 y 100>,
  "nivel_riesgo": "BAJO" | "MEDIO" | "ALTO",
  "resumen_evaluacion": "<texto explicativo detallado de 2 a 3 párrafos técnicos elaborado por Bank-ito>",
  "factores_positivos": ["<fortaleza 1>", "<fortaleza 2>", "<fortaleza 3>"],
  "factores_negativos": ["<debilidad o riesgo 1>", "<debilidad o riesgo 2>"],
  "senales_alerta": ["<alerta preventiva temprana 1>", "<alerta 2>"],
  "probabilidad_morosidad_30d": <flotante porcentaje, ej 5.5>,
  "probabilidad_morosidad_90d": <flotante porcentaje, ej 12.0>,
  "recomendaciones": "<recomendaciones prácticas para el analista: aprobación condicionada, garantías, plazo, monto>"
}"""

    prompt_usuario = f"""Evalúa la siguiente solicitud de crédito para la plataforma CREDIT RISK.
No se incluyen datos protegidos. Basa el análisis en métricas financieras y comportamiento de pago según estándares SBS.

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

    # 1. INTENTO CON GOOGLE GEMINI API (Bank-ito)
    if Config.GEMINI_API_KEY:
        gemini_models = [Config.GEMINI_MODEL, "gemini-flash-lite-latest", "gemini-3-flash-preview", "gemini-3.8-flash", "gemini-flash-latest"]
        for g_model in gemini_models:
            if not g_model:
                continue
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{g_model}:generateContent?key={Config.GEMINI_API_KEY}"
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": f"{prompt_sistema}\n\n{prompt_usuario}\n\nResponde ÚNICAMENTE en JSON válido sin markdown adicional:"
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }
                res = requests.post(url, json=payload, timeout=12)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                        # Limpiar delimitadores markdown si el modelo los incluyó
                        if raw_text.startswith("```json"):
                            raw_text = raw_text[7:]
                        if raw_text.startswith("```"):
                            raw_text = raw_text[3:]
                        if raw_text.endswith("```"):
                            raw_text = raw_text[:-3]
                        resultado = json.loads(raw_text.strip())
                        
                        resultado["modelo_ia_utilizado"] = f"Bank-ito IA (Gemini {g_model})"
                        resultado["es_modo_demo"] = False
                        resultado["aviso_legal"] = "Evaluación generada por Bank-ito IA (Google Gemini) como soporte analítico para el comité de créditos conforme a normas SBS Res. N° 11356-2008."
                        return resultado
            except Exception as err:
                print(f"[WARN] Error con Gemini modelo {g_model}: {err}")
                continue

    # 2. INTENTO CON OPENAI (si está configurado)
    if Config.OPENAI_API_KEY and not Config.OPENAI_API_KEY.startswith("sk-tu-api-key"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=Config.OPENAI_API_KEY)
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
            resultado_ia["modelo_ia_utilizado"] = "Bank-ito IA (OpenAI)"
            resultado_ia["es_modo_demo"] = False
            resultado_ia["aviso_legal"] = "Evaluación generada por Bank-ito IA como herramienta de apoyo analítico. La decisión final corresponde al comité de créditos conforme a normas SBS."
            return resultado_ia
        except Exception as err:
            print(f"[WARN] Error invocando OpenAI API ({err}). Conmutando a motor heurístico...")

    # 3. MOTOR HEURÍSTICO SBS (Respaldo robusto de Bank-ito)
    return generar_evaluacion_heuristica_ia(datos_solicitud, datos_cliente, metricas, motivo="Motor Heurístico SBS")

def generar_evaluacion_heuristica_ia(solicitud: dict, cliente: dict, metricas: dict, motivo: str = "") -> dict:
    """
    Motor Heurístico de IA Explicable Bank-ito para evaluación de solvencia y riesgo SBS.
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

    # Factores según DTI
    if dti <= 35.0:
        factores_positivos.append(f"Ratio Deuda/Ingresos (DTI) sumamente saludable de {dti}%, inferior al umbral prudencial del 35%.")
    elif dti <= 50.0:
        factores_positivos.append(f"Endeudamiento moderado ({dti}%) dentro de parámetros tolerables para crédito productivo.")
        factores_negativos.append(f"Ratio DTI de {dti}% se acerca al límite prudencial máximo del 50%.")
    else:
        factores_negativos.append(f"Sobreendeudamiento crítico: DTI de {dti}% excede el límite del 50%, comprometiendo la liquidez.")
        senales_alerta.append("ALERTA PREVENTIVA: El cliente compromete más del 50% de sus ingresos totales en amortización de pasivos.")

    # Flujo disponible
    if disponible > 0:
        factores_positivos.append(f"Flujo de caja superavitario: Genera S/. {disponible:,.2f} de ingreso libre mensual tras atender la cuota proyectada.")
    else:
        factores_negativos.append(f"Flujo de caja proyectado deficitario (-S/. {abs(disponible):,.2f}). La cuota supera el excedente real.")
        senales_alerta.append("Déficit de cobertura de cuota: Alto riesgo de iliquidez operativa en los primeros 60 días.")

    # Historial crediticio SBS
    if "Puntual" in historial:
        factores_positivos.append("Excelente cultura de pago histórica en el sistema financiero regulado por la SBS.")
    elif "Atrasos leves" in historial:
        factores_negativos.append("Presenta historial con atrasos esporádicos de 1 a 8 días en compromisos pasados.")
        senales_alerta.append("Tendencia a mora temprana: Se sugiere calendarizar fechas de pago coincidentes con cobros de clientes.")
    else:
        factores_negativos.append("Antecedentes de morosidad regularizada o calificación CPP en centrales de riesgo.")
        senales_alerta.append("Historial crediticio con antecedentes de incumplimiento en el último periodo anual.")

    # Situación laboral
    if "formal" in solicitud.get("situacion_laboral", "").lower():
        factores_positivos.append("Estabilidad laboral formal verificable con sustento documentario de flujos.")
    else:
        factores_negativos.append("Actividad en sector informal con variabilidad estacional en ingresos declarados.")
        senales_alerta.append("Requerir inspección in-situ del negocio para validar volumen físico de ventas.")

    # Dictamen según nivel de riesgo
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
        "modelo_ia_utilizado": "Bank-ito IA (Motor Heurístico SBS)",
        "es_modo_demo": False,
        "aviso_legal": "Evaluación asistida por Bank-ito IA orientada a la toma de decisión del comité humano conforme a la normativa SBS Resolución N° 11356-2008."
    }

def consultar_bankito_copilot(pregunta: str, historial: list = None, contexto: dict = None) -> str:
    """
    Copilot y Asistente Financiero Bank-ito.
    Responde consultas de analistas sobre riesgo crediticio, normativa SBS, análisis de clientes y simulación.
    """
    if not pregunta or not pregunta.strip():
        return "Hola, soy **Bank-ito**, tu copiloto de riesgo crediticio. ¿En qué evaluación o consulta financiera puedo ayudarte hoy?"

    contexto_str = ""
    if contexto:
        contexto_str = f"\nContexto del sistema: {json.dumps(contexto, ensure_ascii=False)}"

    prompt_copilot = f"""Eres Bank-ito, el asistente y asesor de Inteligencia Artificial para el Sistema de Evaluación de Riesgo Crediticio de Cajas Municipales de Ahorro y Crédito (CMAC) del Perú (SBS).
Tu personalidad es profesional, sobria, precisa, analítica y orientada a la prudencia financiera.
Responde de manera estructurada con viñetas, cálculos precisos si aplica, y citas de estándares prudenciales (DTI <= 35% ideal, <= 50% máximo tolerable; morosidad SBS Normal, CPP, Deficiente, Dudoso, Pérdida).
Sé conciso y directo, evitando adornos innecesarios.
{contexto_str}

Pregunta del analista:
{pregunta}"""

    # Intento con Gemini
    if Config.GEMINI_API_KEY:
        gemini_models = [Config.GEMINI_MODEL, "gemini-flash-lite-latest", "gemini-3-flash-preview", "gemini-3.8-flash"]
        for g_model in gemini_models:
            if not g_model:
                continue
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{g_model}:generateContent?key={Config.GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt_copilot}]}],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 800
                    }
                }
                res = requests.post(url, json=payload, timeout=10)
                if res.status_code == 200:
                    candidates = res.json().get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                        if text:
                            return text
            except Exception as e:
                print(f"[WARN] Error en copilot con modelo {g_model}: {e}")
                continue

    # Fallback heurístico inteligente
    p_lower = pregunta.lower()
    if "dti" in p_lower or "endeudamiento" in p_lower:
        return (
            "**Cálculo y Parámetros del Ratio DTI (Debt-to-Income) según normativa CMAC/SBS:**\n\n"
            "- **Fórmula:** `DTI = (Total de Pagos Mensuales de Deudas / Ingreso Bruto Mensual) * 100`\n"
            "- **Bajo Riesgo (<= 35%):** El solicitante mantiene un margen amplio de solvencia.\n"
            "- **Riesgo Medio (35% a 50%):** Alerta prudencial; se recomienda exigir aval o garantía real.\n"
            "- **Riesgo Crítico (> 50%):** Sobreendeudamiento severo; se desaconseja aprobación directa sin consolidación o amortización previa."
        )
    elif "sbs" in p_lower or "clasificacion" in p_lower or "calificacion" in p_lower:
        return (
            "**Clasificación Crediticia del Deudor según Resolución SBS N° 11356-2008:**\n\n"
            "1. **Categoría 0 (Normal):** Pagos al día o atrasos menores a 8 días.\n"
            "2. **Categoría 1 (Con Problemas Potenciales - CPP):** Atrasos de 9 a 30 días en créditos microempresa y consumo.\n"
            "3. **Categoría 2 (Deficiente):** Atrasos de 31 a 60 días; requiere provisión específica del 20%.\n"
            "4. **Categoría 3 (Dudoso):** Atrasos de 61 a 120 días; provisión regulatoria del 60%.\n"
            "5. **Categoría 4 (Pérdida):** Atrasos mayores a 120 días; 100% de provisión."
        )
    elif "morosidad" in p_lower or "mora" in p_lower:
        return (
            "**Estrategia de Mitigación de Morosidad Preventiva:**\n\n"
            "- Monitorear alertas en la ventana de 1 a 8 días para evitar pase a cartera CPP.\n"
            "- Alinear cronogramas de pago con los ciclos de liquidez de cada giro del negocio (comercio, servicios o producción).\n"
            "- Utilizar débito automático en cuenta de ahorros para clientes de riesgo bajo y medio."
        )
    else:
        return (
            "**Respuesta de Bank-ito Copilot:**\n\n"
            "Para evaluar adecuadamente el riesgo crediticio de esta operación, te sugiero validar:\n\n"
            "1. **Capacidad de Pago Neta:** Ingresos verificables menos gastos operativos y deudas preexistentes en centrales de riesgo.\n"
            "2. **Cobertura de Cuota:** El ingreso disponible debe superar al menos en un 30% la cuota calculada.\n"
            "3. **Historial SBS:** Priorizar clientes en Categoría Normal (0 días de atraso) y verificar alertas preventivas en la matriz de riesgo."
        )
