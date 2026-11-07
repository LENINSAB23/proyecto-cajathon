"""
Script ejecutor (Runner / Polling) del Bot de Telegram de Credit Risk
Permite atender comandos (/start, /pagar, /deuda, /historial, /promesa, /bankito)
en tiempo real mediante Long Polling, tanto en desarrollo local como en workers de fondo.
"""

import time
import requests
from config import Config
from app import create_app
from services.telegram_service import procesar_mensaje_entrante_telegram

def run_bot_polling():
    app = create_app()
    token = Config.TELEGRAM_BOT_TOKEN
    if not token:
        print("[ERROR] TELEGRAM_BOT_TOKEN no configurado.")
        return

    print("==================================================================")
    print("🤖 INICIANDO BOT INTERACTIVO DE TELEGRAM: @CreditRiskMonitor2bot")
    print("Canal: Credit Risk CMAC - Banca y Cobranzas")
    print("Comandos disponibles: /start, /pagar, /deuda, /historial, /promesa, /bankito, /contacto")
    print("Esperando mensajes de usuarios...")
    print("==================================================================")

    offset = None
    url = f"https://api.telegram.org/bot{token}/getUpdates"

    with app.app_context():
        while True:
            try:
                params = {"timeout": 15}
                if offset:
                    params["offset"] = offset

                res = requests.get(url, params=params, timeout=20)
                if res.status_code == 200:
                    datos = res.json()
                    if datos.get("ok"):
                        updates = datos.get("result", [])
                        for u in updates:
                            update_id = u["update_id"]
                            offset = update_id + 1
                            
                            # Procesar comando o mensaje entrante
                            msg = u.get("message") or u.get("callback_query", {}).get("message")
                            user = (u.get("message") or u.get("callback_query", {})).get("from", {})
                            username = user.get("username") or user.get("first_name") or "Usuario"
                            texto = (u.get("message", {}).get("text") or u.get("callback_query", {}).get("data") or "")
                            
                            print(f"[BOT] Mensaje recibido de @{username}: '{texto}'")
                            resultado = procesar_mensaje_entrante_telegram(u)
                            if resultado.get("enviado"):
                                print(f"[BOT] -> Respuesta enviada a chat {resultado.get('chat_id')}")
                            else:
                                print(f"[BOT] -> Error o no enviado: {resultado.get('motivo') or resultado.get('error')}")

                elif res.status_code == 409:
                    print("[WARN] Conflicto de webhook activo en Telegram. Si usas Polling, debes desactivar el webhook.")
                    time.sleep(5)
                else:
                    time.sleep(2)
            except KeyboardInterrupt:
                print("\n[INFO] Bot detenido por el usuario.")
                break
            except Exception as e:
                print(f"[WARN] Error en polling: {e}")
                time.sleep(3)

if __name__ == "__main__":
    run_bot_polling()

