import os
import requests

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
WEBHOOK_URL = f"https://empathai-bot.onrender.com/webhook"

async def setup_webhook():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook"
    response = requests.post(url, json={"url": WEBHOOK_URL})
    if response.status_code == 200:
        print("✅ Webhook установлен успешно.")
    else:
        print("❌ Ошибка установки webhook:", response.text)

async def handle_update(update):
    # Пока просто для теста — выведем сообщение в консоль
    print("🔹 Пришло сообщение от Telegram:", update)
    return {"ok": True}
