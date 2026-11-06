"""
Servicio de Automatización de Notificaciones a Telegram
Manejo de Telegram Bot API, idempotencia, reintentos y auditoría de alertas de riesgo crediticio.
Cumple estrictamente con la normativa de privacidad y protección de datos financieros.
"""

import os
import time
import requests
from datetime import datetime
from config import Config
from database.db import new_id, query_db, execute_db

# Cache en memoria para chat_id auto-descubierto durante la ejecución
_CACHE_CHAT_ID = None

def obtener_chat_id_telegram(bot_token: str = None) -> str:
    """
    Obtiene el Chat ID de Telegram:
    1. Si está configurado en TELEGRAM_CHAT_ID de las variables de entorno, lo usa.
    2. Si no, consulta getUpdates de la Bot API para descubrir el chat del usuario que inició el bot.
    """
    global _CACHE_CHAT_ID

    token = bot_token or Config.TELEGRAM_BOT_TOKEN
    if not token:
        return None

    # 1. Configuración explícita en entorno
    chat_id = Config.TELEGRAM_CHAT_ID or os.getenv("TELEGRAM_CHAT_ID", "")
    if chat_id and chat_id.strip():
        return chat_id.strip()

    # 2. Cache en memoria
    if _CACHE_CHAT_ID:
        return _CACHE_CHAT_ID

    # 3. Auto-descubrimiento mediante getUpdates
    try:
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            datos = res.json()
            if datos.get("ok") and datos.get("result"):
                # Obtener el último mensaje recibido
                ultimo_update = datos["result"][-1]
                msg = ultimo_update.get("message") or ultimo_update.get("channel_post") or ultimo_update.get("my_chat_member", {}).get("chat")
                if msg:
                    chat = msg.get("chat") or msg
                    discovered_id = str(chat.get("id", ""))
                    if discovered_id:
                        _CACHE_CHAT_ID = discovered_id
                        print(f"[INFO] Chat ID de Telegram auto-descubierto con éxito: {_CACHE_CHAT_ID}")
                        return _CACHE_CHAT_ID
    except Exception as e:
        print(f"[WARN] Error al consultar getUpdates de Telegram: {e}")

    return None

def ya_fue_notificado(evaluacion_id: str = None, solicitud_id: str = None, tipo_alerta: str = "RIESGO_ALTO") -> bool:
    """
    Regla de Idempotencia:
    Verifica en la tabla notificaciones_telegram si ya se envió exitosamente una alerta
    para la misma evaluación o solicitud, evitando duplicados.
    """
    if not evaluacion_id and not solicitud_id:
        return False

    try:
        if evaluacion_id:
            res = query_db("""
                SELECT COUNT(*) as cnt FROM notificaciones_telegram
                WHERE evaluacion_id = ? AND tipo_alerta = ? AND estado_envio = 'ENVIADO'
            """, (evaluacion_id, tipo_alerta), one=True)
            if res and res['cnt'] > 0:
                return True

        if solicitud_id:
            res = query_db("""
                SELECT COUNT(*) as cnt FROM notificaciones_telegram
                WHERE solicitud_id = ? AND tipo_alerta = ? AND estado_envio = 'ENVIADO'
            """, (solicitud_id, tipo_alerta), one=True)
            if res and res['cnt'] > 0:
                return True
    except Exception as e:
        print(f"[WARN] No se pudo verificar duplicados en notificaciones_telegram ({e}). Procediendo con cautela.")

    return False

def formatear_mensaje_alerta(codigo_cliente: str, numero_solicitud: str, nivel_riesgo: str, motivo: str, fecha_eval: str = None) -> str:
    """
    Formatea el mensaje exactamente con la plantilla requerida.
    REGLA ESTRICTA: No incluye DNI, teléfono, dirección ni montos sensibles.
    """
    fecha = fecha_eval or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    mensaje = (
        "🚨 ALERTA DE RIESGO CREDITICIO\n\n"
        "Se ha detectado un crédito que requiere atención.\n\n"
        f"Código del cliente: {codigo_cliente}\n"
        f"Código del crédito: {numero_solicitud}\n"
        f"Nivel de riesgo: {nivel_riesgo.upper()}\n"
        f"Motivo: {motivo}\n"
        f"Fecha: {fecha}\n\n"
        "⚠️ Se recomienda revisar el caso en la plataforma."
    )
    return mensaje

def registrar_notificacion_en_bd(evaluacion_id: str, solicitud_id: str, cliente_id: str, chat_id: str, tipo_alerta: str, nivel_riesgo: str, mensaje: str, estado_envio: str, reintentos: int = 0, error_detalle: str = None):
    """
    Registra el estado de la notificación en la base de datos (PostgreSQL / SQLite).
    """
    try:
        notif_id = new_id("ntf")
        execute_db("""
            INSERT INTO notificaciones_telegram (
                id, evaluacion_id, solicitud_id, cliente_id, chat_id,
                tipo_alerta, nivel_riesgo, mensaje, estado_envio, reintentos, error_detalle
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            notif_id, evaluacion_id, solicitud_id, cliente_id,
            chat_id or "NO_CONFIGURADO", tipo_alerta, nivel_riesgo,
            mensaje, estado_envio, reintentos, error_detalle
        ))
    except Exception as e:
        print(f"[WARN] Error al registrar notificación en base de datos: {e}")

def enviar_mensaje_telegram(mensaje: str, chat_id: str = None, max_reintentos: int = 3) -> dict:
    """
    Envía un mensaje a la API de Telegram con política de reintentos automáticos.
    """
    token = Config.TELEGRAM_BOT_TOKEN or os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return {"enviado": False, "motivo": "TELEGRAM_BOT_TOKEN no configurado en variables de entorno"}

    target_chat_id = chat_id or obtener_chat_id_telegram(token)
    if not target_chat_id:
        return {
            "enviado": False,
            "motivo": "TELEGRAM_CHAT_ID no configurado y no se detectaron mensajes en el bot. Envía /start a @CreditRiskMonitor2bot"
        }

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": target_chat_id,
        "text": mensaje
    }

    ultimo_error = None
    for intento in range(1, max_reintentos + 1):
        try:
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                if data.get("ok"):
                    return {
                        "enviado": True,
                        "chat_id": target_chat_id,
                        "intentos": intento,
                        "message_id": data.get("result", {}).get("message_id")
                    }
                else:
                    ultimo_error = f"Telegram API devolvió ok=False: {data.get('description')}"
            else:
                ultimo_error = f"HTTP {res.status_code}: {res.text}"
        except Exception as e:
            ultimo_error = f"Excepción de conexión (intento {intento}/{max_reintentos}): {e}"

        if intento < max_reintentos:
            time.sleep(1.0)

    return {
        "enviado": False,
        "chat_id": target_chat_id,
        "intentos": max_reintentos,
        "error": ultimo_error
    }

def procesar_alerta_riesgo_automatica(datos_evaluacion: dict, datos_solicitud: dict, datos_cliente: dict) -> dict:
    """
    Función principal de automatización de alertas:
    - Evalúa el nivel de riesgo según las reglas del proyecto.
    - Riesgo BAJO: Guarda la evaluación sin alerta.
    - Riesgo MEDIO: Guarda la evaluación sin alerta crítica.
    - Riesgo ALTO: Envía automáticamente una alerta estructurada a Telegram.
    - Aplica idempotencia para evitar duplicados.
    """
    nivel_riesgo = str(datos_evaluacion.get("nivel_riesgo", "")).upper()
    solicitud_id = datos_solicitud.get("id")
    evaluacion_id = datos_evaluacion.get("id")
    cliente_id = datos_cliente.get("id")
    codigo_cliente = datos_cliente.get("codigo_cliente", f"CLI-{cliente_id[:8]}" if cliente_id else "CLI-DESCONOCIDO")
    numero_solicitud = datos_solicitud.get("numero_solicitud", "SOL-DESCONOCIDO")
    ratio_dti = float(datos_solicitud.get("ratio_dti", 0))

    # Regla 2: Solo Riesgo ALTO (o condición real crítica de sobreendeudamiento DTI > 50%) detona alerta a Telegram
    es_riesgo_critico = (nivel_riesgo == "ALTO" or ratio_dti > 50.0)

    if not es_riesgo_critico:
        return {
            "alerta_emitida": False,
            "motivo": f"Nivel de riesgo {nivel_riesgo} (DTI {ratio_dti}%) dentro de parámetros tolerables. No requiere alerta crítica."
        }

    # Verificar si ya fue notificado previamente (idempotencia)
    if ya_fue_notificado(evaluacion_id=evaluacion_id, solicitud_id=solicitud_id, tipo_alerta="RIESGO_ALTO"):
        return {
            "alerta_emitida": False,
            "motivo": "Alerta ya enviada previamente a Telegram para esta evaluación (idempotencia verificada)."
        }

    # Extraer el motivo real de la evaluación según criterios analíticos del proyecto
    motivo = None
    alertas_senales = datos_evaluacion.get("senales_alerta")
    if alertas_senales:
        if isinstance(alertas_senales, str):
            try:
                import json
                alertas_senales = json.loads(alertas_senales)
            except Exception:
                pass
        if isinstance(alertas_senales, list) and len(alertas_senales) > 0:
            motivo = alertas_senales[0]

    if not motivo:
        factores_neg = datos_evaluacion.get("factores_negativos")
        if factores_neg:
            if isinstance(factores_neg, str):
                try:
                    import json
                    factores_neg = json.loads(factores_neg)
                except Exception:
                    pass
            if isinstance(factores_neg, list) and len(factores_neg) > 0:
                motivo = factores_neg[0]

    if not motivo:
        if ratio_dti > 50.0:
            motivo = f"Sobreendeudamiento crítico: Ratio DTI ({ratio_dti}%) supera el umbral prudencial del 50%."
        else:
            motivo = f"Puntaje de scoring insuficiente ({datos_evaluacion.get('score_riesgo', 0)}/100) y capacidad de pago deficitaria."

    # Formatear el mensaje según plantilla oficial
    fecha_eval = datos_evaluacion.get("created_at")
    if fecha_eval and len(str(fecha_eval)) >= 19:
        fecha_eval = str(fecha_eval)[:19]
    else:
        fecha_eval = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    mensaje = formatear_mensaje_alerta(
        codigo_cliente=codigo_cliente,
        numero_solicitud=numero_solicitud,
        nivel_riesgo="ALTO",
        motivo=motivo,
        fecha_eval=fecha_eval
    )

    # Enviar a Telegram
    chat_id = obtener_chat_id_telegram()
    resultado_envio = enviar_mensaje_telegram(mensaje, chat_id=chat_id)

    # Registrar en tabla auxiliar notificaciones_telegram
    estado = "ENVIADO" if resultado_envio.get("enviado") else "FALLIDO"
    intentos = resultado_envio.get("intentos", 1)
    error_detalle = resultado_envio.get("error") or resultado_envio.get("motivo")

    registrar_notificacion_en_bd(
        evaluacion_id=evaluacion_id,
        solicitud_id=solicitud_id,
        cliente_id=cliente_id,
        chat_id=chat_id,
        tipo_alerta="RIESGO_ALTO",
        nivel_riesgo="ALTO",
        mensaje=mensaje,
        estado_envio=estado,
        reintentos=intentos,
        error_detalle=error_detalle
    )

    return {
        "alerta_emitida": resultado_envio.get("enviado", False),
        "estado": estado,
        "chat_id": chat_id,
        "motivo": motivo,
        "detalle": resultado_envio
    }
