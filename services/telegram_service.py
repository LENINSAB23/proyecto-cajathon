import logging

import requests
from flask import current_app

from database.db import execute_db, query_db

logger = logging.getLogger(__name__)


def notify_telegram(event_key, message):
    """Send an optional Telegram notification once per event without blocking workflows."""
    token = current_app.config.get("TELEGRAM_BOT_TOKEN")
    chat_id = current_app.config.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False

    try:
        if query_db("SELECT event_key FROM telegram_notifications WHERE event_key = ?", (event_key,), one=True):
            return False
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message[:4000]},
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            logger.warning("Telegram rechazó una notificación del evento %s", event_key)
            return False
        execute_db(
            "INSERT INTO telegram_notifications (event_key) VALUES (?)",
            (event_key,),
        )
        return True
    except Exception:
        logger.warning("No se pudo enviar notificación de Telegram para el evento %s", event_key)
        return False
