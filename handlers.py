import os
import requests
import openai

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
ASSISTANT_ID = os.environ["ASSISTANT_ID"]
WEBHOOK_URL = "https://empathai-bot.onrender.com/webhook"

openai.api_key = OPENAI_API_KEY

async def setup_webhook():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook"
    response = requests.post(url, json={"url": WEBHOOK_URL})
    if response.status_code == 200:
        print("✅ Webhook установлен успешно.")
    else:
        print("❌ Ошибка установки webhook:", response.text)

async def handle_update(update):
    if "message" not in update:
        return {"ok": True}

    chat_id = update["message"]["chat"]["id"]
    user_message = update["message"].get("text", "")

    # --- создаём поток в OpenAI Assistant API ---
    try:
        thread = openai.beta.threads.create()
        thread_id = thread.id

        openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )

        run = openai.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        # ждём завершения ответа (простая синхронная проверка)
        while True:
            run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if run_status.status == "completed":
                break

        messages = openai.beta.threads.messages.list(thread_id=thread_id)
        assistant_reply = messages.data[0].content[0].text.value

    except Exception as e:
        assistant_reply = "Произошла ошибка при обращении к ИИ. Попробуйте позже."

    # --- отправляем ответ пользователю в Telegram ---
    reply_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": assistant_reply
    }
    requests.post(reply_url, json=payload)

    return {"ok": True}
