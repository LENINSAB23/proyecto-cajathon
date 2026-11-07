"""
Rutas del Webhook y Bot Interactivo de Telegram
Recibe actualizaciones en tiempo real y gestiona comandos financieros de autogestión.
"""

from flask import Blueprint, request, jsonify, url_for, current_app, session
from services.telegram_service import (
    procesar_mensaje_entrante_telegram,
    configurar_webhook_telegram,
    obtener_info_webhook,
    enviar_mensaje_telegram,
    obtener_chat_id_telegram,
    obtener_teclado_principal,
    registrar_notificacion_en_bd
)

telegram_bp = Blueprint('telegram', __name__, url_prefix='/telegram')

@telegram_bp.route('/enviar-mensaje', methods=['POST'])
def enviar_mensaje_manual():
    """
    Permite a los usuarios autorizados (Administrador, Analista, Cobranzas)
    enviar notificaciones directas o plantillas a Telegram desde la plataforma web.
    Las alertas automáticas de riesgo alto continúan activas e ininterrumpidas.
    """
    if not session.get('user_id'):
        return jsonify({"ok": False, "error": "Acceso no autorizado. Inicie sesión en la plataforma."}), 401

    payload = request.get_json(silent=True) or request.form.to_dict()
    mensaje = (payload.get('mensaje') or '').strip()
    chat_id = (payload.get('chat_id') or '').strip() or None
    tipo_alerta = (payload.get('tipo_alerta') or 'MENSAJE_MANUAL_WEB').strip()

    if not mensaje:
        return jsonify({"ok": False, "error": "El contenido del mensaje no puede estar vacío."}), 400

    # Envío con teclado institucional interactivo
    resultado = enviar_mensaje_telegram(
        mensaje,
        chat_id=chat_id,
        reply_markup=obtener_teclado_principal()
    )

    estado = "ENVIADO" if resultado.get("enviado") else "FALLIDO"
    target_chat = resultado.get("chat_id") or chat_id or "6237089936"

    # Auditoría en la base de datos
    registrar_notificacion_en_bd(
        evaluacion_id=None,
        solicitud_id=None,
        cliente_id=None,
        chat_id=target_chat,
        tipo_alerta=tipo_alerta,
        nivel_riesgo="MANUAL",
        mensaje=mensaje,
        estado_envio=estado,
        reintentos=resultado.get("intentos", 1),
        error_detalle=resultado.get("error")
    )

    if resultado.get("enviado"):
        return jsonify({
            "ok": True,
            "message": "Notificación entregada exitosamente al chat de Telegram.",
            "chat_id": target_chat,
            "message_id": resultado.get("message_id")
        }), 200
    else:
        err_msg = resultado.get("error") or resultado.get("motivo") or "Error al comunicar con Telegram API"
        return jsonify({"ok": False, "error": err_msg}), 502


@telegram_bp.route('/webhook', methods=['POST'])
def webhook():
    """
    Endpoint principal receptor de eventos de Telegram Bot API.
    Procesa /start, /pagar, /deuda, /historial, /promesa, /bankito y botones interactivos.
    """
    data = request.get_json(force=True, silent=True) or {}
    try:
        resultado = procesar_mensaje_entrante_telegram(data)
        return jsonify({"ok": True, "resultado": resultado}), 200
    except Exception as e:
        print(f"[WARN] Error procesando webhook de Telegram: {e}")
        return jsonify({"ok": False, "error": str(e)}), 200

@telegram_bp.route('/setup-webhook', methods=['GET', 'POST'])
def setup_webhook():
    """
    Configura automáticamente el Webhook en Telegram Bot API con la URL pública actual.
    """
    # Detectar URL pública o parámetro explícito
    custom_url = request.args.get('url', '').strip()
    if custom_url:
        webhook_target = custom_url.rstrip('/') + '/telegram/webhook'
    else:
        # Usar la URL pública del host actual (Render o dominio configurado)
        base_url = request.host_url.rstrip('/')
        if base_url.startswith("http://") and "localhost" not in base_url and "127.0.0.1" not in base_url:
            base_url = base_url.replace("http://", "https://")
        webhook_target = f"{base_url}/telegram/webhook"

    res = configurar_webhook_telegram(webhook_target)
    return jsonify({
        "status": "success" if res.get("ok") else "error",
        "webhook_url": webhook_target,
        "telegram_response": res
    })

@telegram_bp.route('/info', methods=['GET'])
def info_webhook():
    """Retorna información del Webhook y estado de conexión con Telegram."""
    info = obtener_info_webhook()
    chat_id = obtener_chat_id_telegram()
    return jsonify({
        "webhook_info": info,
        "chat_id_detectado": chat_id,
        "bot_username": "@CreditRiskMonitor2bot"
    })

