"""
Rutas del Webhook y Bot Interactivo de Telegram
Recibe actualizaciones en tiempo real y gestiona comandos financieros de autogestión.
"""

from flask import Blueprint, request, jsonify, url_for, current_app
from services.telegram_service import (
    procesar_mensaje_entrante_telegram,
    configurar_webhook_telegram,
    obtener_info_webhook,
    enviar_mensaje_telegram,
    obtener_chat_id_telegram
)

telegram_bp = Blueprint('telegram', __name__, url_prefix='/telegram')

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

