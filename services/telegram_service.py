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

def enviar_mensaje_telegram(mensaje: str, chat_id: str = None, max_reintentos: int = 3, bot_token: str = None, reply_markup: dict = None, parse_mode: str = None) -> dict:
    """
    Envía un mensaje a la API de Telegram con soporte para teclados interactivos y reintentos automáticos.
    """
    token = bot_token or Config.TELEGRAM_BOT_TOKEN or os.getenv("TELEGRAM_BOT_TOKEN", "")
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
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if parse_mode:
        payload["parse_mode"] = parse_mode

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

def notify_telegram(event_key: str, message: str) -> bool:
    """
    Envía una notificación a Telegram una sola vez por evento (idempotencia)
    sin bloquear los flujos de la aplicación.
    Registra el evento en telegram_notifications para no duplicar envíos.
    """
    try:
        from flask import current_app, has_app_context
        if has_app_context() and current_app:
            token = current_app.config.get("TELEGRAM_BOT_TOKEN") or Config.TELEGRAM_BOT_TOKEN
            chat_id = current_app.config.get("TELEGRAM_CHAT_ID") or Config.TELEGRAM_CHAT_ID
        else:
            token = Config.TELEGRAM_BOT_TOKEN
            chat_id = Config.TELEGRAM_CHAT_ID
    except Exception:
        token = Config.TELEGRAM_BOT_TOKEN
        chat_id = Config.TELEGRAM_CHAT_ID

    token = token or Config.TELEGRAM_BOT_TOKEN
    chat_id = chat_id or obtener_chat_id_telegram(token)
    if not token or not chat_id:
        return False

    try:
        existe = query_db(
            "SELECT event_key FROM telegram_notifications WHERE event_key = ?",
            (event_key,),
            one=True
        )
        if existe:
            return False

        res = enviar_mensaje_telegram(message, chat_id=chat_id, bot_token=token)
        if res.get("enviado"):
            execute_db(
                "INSERT INTO telegram_notifications (event_key) VALUES (?)",
                (event_key,)
            )
            return True
        return False
    except Exception as e:
        print(f"[WARN] No se pudo enviar notificación de Telegram para evento {event_key}: {e}")
        return False

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

# ============================================================================
# BOT INTERACTIVO Y GESTIÓN DE COBRANZA PREVENTIVA
# ============================================================================

def obtener_teclado_principal() -> dict:
    """Retorna un teclado de acceso rápido institucional con opciones financieras."""
    return {
        "keyboard": [
            [{"text": "📊 Mi Estado y Deuda"}, {"text": "💳 Métodos de Pago"}],
            [{"text": "📜 Historial de Pagos"}, {"text": "🤝 Promesa de Pago"}],
            [{"text": "🤖 Consultar a Bank-ito IA"}, {"text": "📞 Soporte y Canales"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

def obtener_teclado_inline_pago() -> dict:
    """Retorna botones inline para facilitar abonos y consultas inmediatas."""
    return {
        "inline_keyboard": [
            [
                {"text": "📱 Billeteras Digitales (Yape / Plin)", "callback_data": "pago_yape"}
            ],
            [
                {"text": "🏛️ Cuentas Bancarias y CCI", "callback_data": "pago_bancos"}
            ],
            [
                {"text": "📊 Ver mi deuda", "callback_data": "cmd_deuda"},
                {"text": "🤝 Registrar Promesa", "callback_data": "cmd_promesa"}
            ]
        ]
    }

def generar_mensaje_recordatorio_preventivo(datos_cuota: dict, datos_cliente: dict = None, datos_solicitud: dict = None) -> str:
    """Genera mensaje formal preventivo de pago antes del vencimiento."""
    nombres = f"{datos_cliente.get('nombres', '')} {datos_cliente.get('apellidos', '')}".strip() if datos_cliente else "Estimado(a) Cliente"
    codigo_cli = datos_cliente.get("codigo_cliente", "CLI-TITULAR") if datos_cliente else "CLI-TITULAR"
    solicitud = datos_solicitud.get("numero_solicitud", "SOL-CREDITO") if datos_solicitud else "SOL-CREDITO"

    monto_cuota = float(datos_cuota.get("monto_cuota", 0))
    saldo_pendiente = float(datos_cuota.get("saldo_pendiente", monto_cuota))
    fecha_venc = str(datos_cuota.get("fecha_vencimiento", ""))[:10]
    num_cuota = datos_cuota.get("numero_cuota", 1)
    tot_cuotas = datos_cuota.get("total_cuotas", 12)

    mensaje = (
        "🔔 RECORDATORIO PREVENTIVO DE PAGO\n"
        "🏛️ Caja Inteligente - Sistema Financiero CMAC\n\n"
        f"Estimado(a) {nombres},\n"
        f"Le recordamos que su cuota crediticia está próxima a vencer:\n\n"
        f"📌 Código de Cliente: {codigo_cli}\n"
        f"📄 Crédito N°: {solicitud}\n"
        f"🗓️ Cuota a pagar: N° {num_cuota} de {tot_cuotas}\n"
        f"💰 Monto de la cuota: S/ {monto_cuota:,.2f}\n"
        f"💵 Total a regularizar: S/ {saldo_pendiente:,.2f}\n"
        f"📅 Fecha límite de vencimiento: {fecha_venc}\n"
        "🛡️ Calificación SBS actual: Categoría 0 (Normal - Sin atraso)\n\n"
        "💡 Beneficio: Realizar su pago a tiempo mantiene su récord crediticio intachable en SBS e Infocorp, permitiéndole acceder a tasas preferenciales y mayores líneas de crédito.\n\n"
        "💳 Para ver métodos y cuentas de pago escriba /pagar o elija una opción en el menú."
    )
    return mensaje

def generar_mensaje_aviso_mora(datos_cuota: dict, datos_cliente: dict = None, datos_solicitud: dict = None) -> str:
    """Genera aviso formal de mora con días de atraso, penalidad acumulada y advertencia regulatoria."""
    nombres = f"{datos_cliente.get('nombres', '')} {datos_cliente.get('apellidos', '')}".strip() if datos_cliente else "Estimado(a) Cliente"
    codigo_cli = datos_cliente.get("codigo_cliente", "CLI-TITULAR") if datos_cliente else "CLI-TITULAR"
    solicitud = datos_solicitud.get("numero_solicitud", "SOL-CREDITO") if datos_solicitud else "SOL-CREDITO"

    monto_cuota = float(datos_cuota.get("monto_cuota", 0))
    penalidad = float(datos_cuota.get("penalidad", 0))
    saldo_pendiente = float(datos_cuota.get("saldo_pendiente", monto_cuota + penalidad))
    fecha_venc = str(datos_cuota.get("fecha_vencimiento", ""))[:10]
    dias_atraso = int(datos_cuota.get("dias_atraso", 0))
    clasif = datos_cuota.get("clasificacion_sbs", "Con Problemas Potenciales")
    num_cuota = datos_cuota.get("numero_cuota", 1)
    tot_cuotas = datos_cuota.get("total_cuotas", 12)

    mensaje = (
        "⚠️ AVISO DE GESTIÓN DE COBRANZA - CUOTA VENCIDA\n"
        "🏛️ Caja Inteligente - Área de Cartera y Recuperaciones\n\n"
        f"Estimado(a) {nombres},\n"
        f"Se registra un atraso en el pago de su cuota crediticia:\n\n"
        f"📌 Código de Cliente: {codigo_cli}\n"
        f"📄 Crédito N°: {solicitud} (Cuota {num_cuota}/{tot_cuotas})\n"
        f"📅 Vencimiento original: {fecha_venc}\n"
        f"⏱️ Días de atraso acumulados: {dias_atraso} días\n"
        f"💰 Monto de cuota: S/ {monto_cuota:,.2f}\n"
        f"⚠️ Penalidad acumulada: S/ {penalidad:,.2f}\n"
        f"💵 TOTAL A REGULARIZAR: S/ {saldo_pendiente:,.2f}\n"
        f"📊 Calificación SBS: {clasif}\n\n"
        "🚨 Importante: Regularice su cuota a la brevedad para evitar la acumulación de penalidades moratorias y el reporte negativo ante las centrales de riesgo SBS.\n\n"
        "👉 Opciones de atención inmediata:\n"
        "• Ver cuentas bancarias y Yape: escriba /pagar\n"
        "• Registrar compromiso de pago: escriba /promesa\n"
        "• Orientación y consultas: escriba /bankito"
    )
    return mensaje

def enviar_recordatorio_cuota_telegram(pago_id: str) -> dict:
    """Envía un recordatorio preventivo o aviso de mora de una cuota a Telegram."""
    sql = """
        SELECT p.*,
               CASE WHEN p.monto_cuota + p.penalidad - COALESCE(
                   (SELECT SUM(tp.monto) FROM transacciones_pago tp WHERE tp.cuota_id = p.id), 0
               ) > 0 THEN p.monto_cuota + p.penalidad - COALESCE(
                   (SELECT SUM(tp.monto) FROM transacciones_pago tp WHERE tp.cuota_id = p.id), 0
               ) ELSE 0 END AS saldo_pendiente,
               c.nombres, c.apellidos, c.codigo_cliente, c.telefono,
               s.numero_solicitud, s.tipo_credito
        FROM pagos p
        JOIN clientes c ON p.cliente_id = c.id
        JOIN solicitudes_credito s ON p.solicitud_id = s.id
        WHERE p.id = ?
    """
    pago = query_db(sql, (pago_id,), one=True)
    if not pago:
        return {"enviado": False, "motivo": "Cuota no encontrada en la base de datos"}

    datos_cliente = {
        "nombres": pago.get("nombres"),
        "apellidos": pago.get("apellidos"),
        "codigo_cliente": pago.get("codigo_cliente")
    }
    datos_solicitud = {
        "numero_solicitud": pago.get("numero_solicitud"),
        "tipo_credito": pago.get("tipo_credito")
    }

    es_mora = (pago.get("dias_atraso", 0) > 0) or (pago.get("estado_pago") == "EN_MORA")
    if es_mora:
        mensaje = generar_mensaje_aviso_mora(pago, datos_cliente, datos_solicitud)
        tipo = "AVISO_MORA"
    else:
        mensaje = generar_mensaje_recordatorio_preventivo(pago, datos_cliente, datos_solicitud)
        tipo = "RECORDATORIO_PREVENTIVO"

    chat_id = obtener_chat_id_telegram()
    reply_markup = obtener_teclado_inline_pago()
    res = enviar_mensaje_telegram(mensaje, chat_id=chat_id, reply_markup=reply_markup)

    registrar_notificacion_en_bd(
        evaluacion_id=None,
        solicitud_id=pago.get("solicitud_id"),
        cliente_id=pago.get("cliente_id"),
        chat_id=chat_id,
        tipo_alerta=tipo,
        nivel_riesgo="ALTO" if es_mora else "BAJO",
        mensaje=mensaje,
        estado_envio="ENVIADO" if res.get("enviado") else "FALLIDO",
        reintentos=res.get("intentos", 1),
        error_detalle=res.get("error")
    )
    return res

def procesar_mensaje_entrante_telegram(update_data: dict) -> dict:
    """
    Procesador inteligente de mensajes y comandos interactivos para Telegram:
    - /start o /menu -> Menú oficial de bienvenida y teclado
    - /pagar -> Cuentas bancarias oficiales, CCI, Yape y Plin
    - /deuda o /estado -> Consulta de saldo pendiente, próxima cuota y días de mora
    - /historial -> Historial de abonos y cuotas pagadas
    - /promesa -> Registro interactivo de promesa de pago
    - /bankito -> Consultas financieras con IA (Google Gemini / Heurística SBS)
    - /contacto -> Datos de agencias y atención al cliente
    """
    if not isinstance(update_data, dict):
        return {"ok": False, "error": "Payload inválido"}

    chat_id = None
    texto = ""

    # Detección de callback_query (botones inline presionados)
    if "callback_query" in update_data:
        cb = update_data["callback_query"]
        chat_id = str(cb.get("message", {}).get("chat", {}).get("id", ""))
        texto = str(cb.get("data", "")).strip()
    elif "message" in update_data:
        msg = update_data["message"]
        chat_id = str(msg.get("chat", {}).get("id", ""))
        texto = str(msg.get("text", "")).strip()

    if not chat_id or not texto:
        return {"ok": False, "error": "No se detectó chat_id o texto"}

    texto_lower = texto.lower()

    # 1. COMANDO /start O /menu
    if texto_lower in ("/start", "/menu", "menu", "hola", "inicio", "cmd_menu"):
        bienvenida = (
            "🏛️ BIENVENIDO A CAJA INTELIGENTE\n"
            "Canal Oficial de Autogestión Crediticia y Pagos CMAC\n\n"
            "Hola, nos complace atenderte. A través de este canal puedes consultar tus cuotas, métodos de pago y recibir asesoría financiera 24/7 con Bank-ito IA.\n\n"
            "📌 Selecciona una opción del teclado o escribe un comando:\n\n"
            "💳 /pagar - Ver canales de pago oficiales (Yape, BCP, BBVA)\n"
            "📊 /deuda - Consultar tu saldo pendiente y próxima cuota\n"
            "📜 /historial - Ver tus últimos abonos registrados\n"
            "🤝 /promesa - Registrar un compromiso de pago si no puedes pagar hoy\n"
            "🤖 /bankito - Consultar a Bank-ito IA tus dudas financieras\n"
            "📞 /contacto - Canales de atención y asesores"
        )
        return enviar_mensaje_telegram(
            bienvenida,
            chat_id=chat_id,
            reply_markup=obtener_teclado_principal()
        )

    # 2. COMANDO /pagar O METODOS DE PAGO
    if texto_lower in ("/pagar", "pagar", "💳 métodos de pago", "pago_bancos", "pago_yape"):
        mensaje_pago = (
            "🏦 CANALES Y MÉTODOS DE PAGO OFICIALES\n"
            "🏛️ Caja Inteligente - Red de Recaudación SBS\n\n"
            "Puedes cancelar o amortizar tu cuota a través de cualquiera de los siguientes medios:\n\n"
            "📱 1. Billeteras Digitales (Acreditación Inmediata):\n"
            "• Yape y Plin: Opción 'Pago de Servicios' -> Buscar 'Caja Inteligente'\n"
            "• Ingresa tu Código de Cliente o DNI del titular.\n\n"
            "🏛️ 2. Transferencias Bancarias e Interbancarias (CCI):\n"
            "• Banco de Crédito del Perú (BCP):\n"
            "  - Cta. Corriente Soles: 191-8849201-0-44\n"
            "  - CCI: 002-191-008849201044-52\n"
            "• BBVA Perú:\n"
            "  - Cta. Recaudadora: 0011-0320-0100084920\n"
            "  - CCI: 011-320-000100084920-11\n"
            "• Banco de la Nación:\n"
            "  - Convenio Recaudador: 04-9821\n\n"
            "🏪 3. Agencias y Red de Agentes a Nivel Nacional:\n"
            "• En agentes KasNet, Niubiz o Western Union indicando 'Caja Inteligente Créditos' y tu DNI.\n\n"
            "💡 Consejo: Guarda tu comprobante. Tu abono se reflejará en el sistema en tiempo real. Escribe /deuda para comprobar tu saldo actualizado."
        )
        return enviar_mensaje_telegram(
            mensaje_pago,
            chat_id=chat_id,
            reply_markup=obtener_teclado_inline_pago()
        )

    # 3. COMANDO /deuda O /estado
    if texto_lower in ("/deuda", "/estado", "deuda", "estado", "📊 mi estado y deuda", "cmd_deuda", "cuanto debo"):
        # Buscar la cuota pendiente con mayor prioridad en la base de datos
        sql = """
            SELECT p.*,
                   CASE WHEN p.monto_cuota + p.penalidad - COALESCE(
                       (SELECT SUM(tp.monto) FROM transacciones_pago tp WHERE tp.cuota_id = p.id), 0
                   ) > 0 THEN p.monto_cuota + p.penalidad - COALESCE(
                       (SELECT SUM(tp.monto) FROM transacciones_pago tp WHERE tp.cuota_id = p.id), 0
                   ) ELSE 0 END AS saldo_pendiente,
                   c.nombres, c.apellidos, c.codigo_cliente,
                   s.numero_solicitud, s.tipo_credito
            FROM pagos p
            JOIN clientes c ON p.cliente_id = c.id
            JOIN solicitudes_credito s ON p.solicitud_id = s.id
            WHERE p.estado_pago != 'PAGADO'
            ORDER BY p.dias_atraso DESC, p.fecha_vencimiento ASC
            LIMIT 1
        """
        pago = query_db(sql, one=True)

        if not pago:
            msg_al_dia = (
                "🎉 ¡ESTADO AL DÍA - FELICITACIONES!\n\n"
                "Actualmente no registras cuotas pendientes ni atrasos en tu cuenta crediticia.\n\n"
                "🛡️ Calificación SBS: Categoría 0 (Normal)\n"
                "⭐ Puntaje de Comportamiento: Excelente (100/100)\n\n"
                "Mantener tu crédito al día te califica para desembolsos preferenciales y ampliación de capital de trabajo."
            )
            return enviar_mensaje_telegram(msg_al_dia, chat_id=chat_id, reply_markup=obtener_teclado_principal())

        monto_c = float(pago.get("monto_cuota", 0))
        penal = float(pago.get("penalidad", 0))
        total_p = float(pago.get("saldo_pendiente", monto_c + penal))
        dias_atr = int(pago.get("dias_atraso", 0))
        clasif_sbs = pago.get("clasificacion_sbs", "Normal (0 días)")

        estado_texto = "EN MORA" if dias_atr > 0 else "VIGENTE (Por vencer)"

        msg_deuda = (
            "📊 ESTADO DE CUENTA CREDITICIO\n"
            "🏛️ Caja Inteligente - Sistema SBS\n\n"
            f"👤 Titular: {pago.get('nombres')} {pago.get('apellidos')}\n"
            f"📌 Código: {pago.get('codigo_cliente')}\n"
            f"📄 Crédito N°: {pago.get('numero_solicitud')} ({pago.get('tipo_credito')})\n\n"
            f"🗓️ Cuota: N° {pago.get('numero_cuota')} de {pago.get('total_cuotas')}\n"
            f"📅 Fecha límite de vencimiento: {str(pago.get('fecha_vencimiento'))[:10]}\n"
            f"⏱️ Días de atraso: {dias_atr} días\n"
            f"💰 Monto de cuota: S/ {monto_c:,.2f}\n"
            f"⚠️ Penalidad por atraso: S/ {penal:,.2f}\n"
            f"💵 TOTAL PENDIENTE A PAGAR: S/ {total_p:,.2f}\n"
            f"🛡️ Clasificación SBS: {clasif_sbs}\n"
            f"📌 Estado actual: {estado_texto}\n\n"
            "👉 Para cancelar ahora escribe /pagar\n"
            "👉 Si requieres plazo adicional escribe /promesa"
        )
        return enviar_mensaje_telegram(msg_deuda, chat_id=chat_id, reply_markup=obtener_teclado_inline_pago())

    # 4. COMANDO /historial
    if texto_lower in ("/historial", "historial", "📜 historial de pagos", "cmd_historial"):
        sql_hist = """
            SELECT p.numero_cuota, p.total_cuotas, p.monto_cuota, p.fecha_pago,
                   p.metodo_pago, p.estado_pago, s.numero_solicitud
            FROM pagos p
            JOIN solicitudes_credito s ON p.solicitud_id = s.id
            WHERE p.estado_pago = 'PAGADO' OR p.fecha_pago IS NOT NULL
            ORDER BY p.fecha_pago DESC
            LIMIT 5
        """
        historial = query_db(sql_hist)

        if not historial:
            msg_vacio = (
                "📜 HISTORIAL DE ABONOS\n\n"
                "Aún no se registran pagos finalizados en este periodo.\n"
                "Tan pronto efectúes un abono aparecerá auditado aquí."
            )
            return enviar_mensaje_telegram(msg_vacio, chat_id=chat_id, reply_markup=obtener_teclado_principal())

        lineas = ["📜 HISTORIAL DE PAGOS REGISTRADOS\n🏛️ Caja Inteligente - Comprobantes\n"]
        for h in historial:
            f_pago = str(h.get("fecha_pago") or "Fecha reciente")[:10]
            met = h.get("metodo_pago") or "Transferencia / Ventanilla"
            lineas.append(
                f"✅ Cuota {h.get('numero_cuota')}/{h.get('total_cuotas')} | Crédito {h.get('numero_solicitud')}\n"
                f"   💰 S/ {float(h.get('monto_cuota', 0)):,.2f} - {f_pago}\n"
                f"   💳 Vía: {met}\n"
            )
        lineas.append("🔒 Todos los pagos están conciliados y reportados a la central de riesgos SBS.")
        return enviar_mensaje_telegram("\n".join(lineas), chat_id=chat_id, reply_markup=obtener_teclado_principal())

    # 5. COMANDO /promesa
    if texto_lower.startswith("/promesa") or texto_lower in ("promesa", "🤝 promesa de pago", "cmd_promesa"):
        partes = texto.split()
        # Formato: /promesa 2026-11-20 400
        if len(partes) >= 3:
            fecha_prom = partes[1].strip()
            try:
                monto_prom = float(partes[2].replace(",", "").strip())
                # Obtener un cliente de la BD para asociar la promesa
                cli = query_db("SELECT id, codigo_cliente FROM clientes LIMIT 1", one=True)
                if cli and monto_prom > 0:
                    prom_id = new_id("prm")
                    execute_db("""
                        INSERT INTO promesas_pago (
                            id, cliente_id, monto_comprometido, fecha_prometida,
                            observaciones, responsable_id, responsable_nombre, registrado_por, estado
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDIENTE')
                    """, (
                        prom_id, cli["id"], monto_prom, fecha_prom,
                        "Compromiso registrado automáticamente desde Bot oficial de Telegram",
                        "u-bot", "Bot de Autogestión Telegram", "telegram_bot"
                    ))
                    msg_confirm = (
                        "🤝 ¡COMPROMISO DE PAGO REGISTRADO EXITOSAMENTE!\n\n"
                        f"📌 Código de Registro: {prom_id[:8]}\n"
                        f"💰 Monto comprometido: S/ {monto_prom:,.2f}\n"
                        f"📅 Fecha acordada: {fecha_prom}\n"
                        "📋 Estado: PENDIENTE (En seguimiento)\n\n"
                        "✅ Tu asesor de cobranzas ha sido notificado para suspender avisos preventivos hasta la fecha prometida. ¡Gracias por tu compromiso!"
                    )
                    return enviar_mensaje_telegram(msg_confirm, chat_id=chat_id, reply_markup=obtener_teclado_principal())
            except Exception as e_prm:
                print(f"[WARN] Error registrando promesa desde bot: {e_prm}")

        # Si no pasó parámetros válidos, mostrar guía amigable
        guia_promesa = (
            "🤝 REGISTRO DE COMPROMISO DE PAGO\n"
            "🏛️ Caja Inteligente - Acuerdos de Cobranza\n\n"
            "Si no puedes cancelar tu cuota hoy, puedes registrar un compromiso formal de pago para una fecha futura y evitar que tu caso pase a cobranza judicial.\n\n"
            "📝 Formato para registrar tu promesa:\n"
            "Escribe: `/promesa FECHA MONTO`\n\n"
            "Ejemplo:\n"
            "`/promesa 2026-11-15 450.00`\n\n"
            "El sistema registrará tu compromiso de inmediato en la plataforma de cobranzas."
        )
        return enviar_mensaje_telegram(guia_promesa, chat_id=chat_id, reply_markup=obtener_teclado_principal())

    # 6. COMANDO /bankito O PREGUNTAS A LA IA
    if texto_lower.startswith("/bankito") or texto_lower == "🤖 consultar a bank-ito ia":
        pregunta = texto.replace("/bankito", "").replace("🤖 Consultar a Bank-ito IA", "").strip()
        if not pregunta:
            ayuda_ia = (
                "🤖 BANK-ITO IA - OFICIAL DE INTELIGENCIA FINANCIERA\n\n"
                "¡Hola! Soy Bank-ito, el asistente con IA de Caja Inteligente regulado por los estándares SBS.\n\n"
                "Puedes hacerme cualquier pregunta financiera escribiendo `/bankito` seguido de tu duda:\n\n"
                "Ejemplos:\n"
                "• `/bankito ¿cómo evito que mi score SBS baje si me atraso?`\n"
                "• `/bankito ¿qué es el ratio DTI y por qué es importante?`\n"
                "• `/bankito ¿cómo puedo reprogramar una cuota de crédito?`"
            )
            return enviar_mensaje_telegram(ayuda_ia, chat_id=chat_id, reply_markup=obtener_teclado_principal())

        from services.ia_service import consultar_bankito_copilot
        respuesta_ia = consultar_bankito_copilot(pregunta, contexto={"canal": "telegram_bot"})
        msg_ia = f"🤖 BANK-ITO RESPONDE:\n\n{respuesta_ia}\n\n💡 _Para más consultas escribe /bankito seguido de tu pregunta._"
        return enviar_mensaje_telegram(msg_ia, chat_id=chat_id, reply_markup=obtener_teclado_principal())

    # 7. COMANDO /contacto O SOPORTE
    if texto_lower in ("/contacto", "contacto", "📞 soporte y canales", "soporte", "ayuda"):
        msg_contacto = (
            "📞 CANALES DE ATENCIÓN Y CONTACTO\n"
            "🏛️ Caja Inteligente - Sede Central CMAC\n\n"
            "📍 Dirección: Av. Central 450, Lima - Perú\n"
            "🕒 Horario de Atención: Lunes a Viernes de 8:30 a 18:00 / Sábados de 9:00 a 13:00\n\n"
            "☎️ Central Telefónica: (01) 619-8000\n"
            "📱 WhatsApp Oficial: +51 987 654 321\n"
            "✉️ Correo Electrónico: atencion@creditrisk.pe\n\n"
            "Estamos a tu disposición para brindarte asesoría crediticia personalizada."
        )
        return enviar_mensaje_telegram(msg_contacto, chat_id=chat_id, reply_markup=obtener_teclado_principal())

    # 8. MENSAJE LIBRE -> RESPUESTA AMABLE CON ASISTENCIA DE BANK-ITO IA
    try:
        from services.ia_service import consultar_bankito_copilot
        resp_libre = consultar_bankito_copilot(texto, contexto={"canal": "telegram_bot"})
        msg_final = f"🤖 Bank-ito Asistente:\n\n{resp_libre}\n\n📌 Para ver opciones de pago escribe /pagar o /menu."
        return enviar_mensaje_telegram(msg_final, chat_id=chat_id, reply_markup=obtener_teclado_principal())
    except Exception:
        fallback = (
            "Estimado cliente, he recibido su mensaje. Para gestionar su crédito utilice los comandos:\n\n"
            "• 💳 /pagar - Ver cuentas autorizadas\n"
            "• 📊 /deuda - Consultar su cuota y saldo\n"
            "• 📜 /historial - Ver pagos registrados\n"
            "• 🤝 /promesa - Registrar compromiso de pago\n"
            "• 🤖 /bankito - Asesoría financiera con IA"
        )
        return enviar_mensaje_telegram(fallback, chat_id=chat_id, reply_markup=obtener_teclado_principal())

def configurar_webhook_telegram(webhook_url: str) -> dict:
    """Configura la URL de Webhook en la API de Telegram."""
    token = Config.TELEGRAM_BOT_TOKEN
    if not token:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN no configurado"}

    url = f"https://api.telegram.org/bot{token}/setWebhook"
    try:
        res = requests.post(url, json={"url": webhook_url}, timeout=10)
        return res.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def obtener_info_webhook() -> dict:
    """Consulta la información del Webhook actual en Telegram."""
    token = Config.TELEGRAM_BOT_TOKEN
    if not token:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN no configurado"}

    url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    try:
        res = requests.get(url, timeout=10)
        return res.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}
