import os
import requests
import openai
from sqlalchemy.orm import Session
from db import SessionLocal
from models import User

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
ASSISTANT_ID = os.environ["ASSISTANT_ID"]
WEBHOOK_URL = "https://empathai-bot.onrender.com/webhook"
FREE_MESSAGES_LIMIT = int(os.environ.get("FREE_MESSAGES_LIMIT", 50))

openai.api_key = OPENAI_API_KEY

async def setup_webhook():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook"
    response = requests.post(url, json={"url": WEBHOOK_URL})
    if response.status_code == 200:
        print("✅ Webhook установлен успешно.")
    else:
        print("❌ Ошибка установки webhook:", response.text)

def get_or_create_user(db: Session, telegram_id: str) -> User:
    user = db.query(User).filter_by(telegram_id=telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id, free_messages_used=0, thread_id=None)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

async def handle_update(update):
    if "message" not in update:
        return {"ok": True}

    chat_id = update["message"]["chat"]["id"]
    user_message = update["message"].get("text", "")

    db = SessionLocal()
    user = get_or_create_user(db, str(chat_id))

    # проверка лимита
    if user.free_messages_used >= FREE_MESSAGES_LIMIT:
        send_message(chat_id, "🔒 Превышен лимит бесплатных сообщений. Чтобы продолжить, оформите подписку.")
        db.close()
        return {"ok": True}

    try:
        # если у пользователя ещё нет thread_id — создаём
        if not user.thread_id:
            thread = openai.beta.threads.create()
            user.thread_id = thread.id
            db.commit()

        # создаём сообщение
        openai.beta.threads.messages.create(
            thread_id=user.thread_id,
            role="user",
            content=user_message
        )

        run = openai.beta.threads.runs.create(
            thread_id=user.thread_id,
            assistant_id=ASSISTANT_ID
        )

        # ждём завершения
        while True:
            run_status = openai.beta.threads.runs.retrieve(thread_id=user.thread_id, run_id=run.id)
            if run_status.status == "completed":
                break

        messages = openai.beta.threads.messages.list(thread_id=user.thread_id)
        assistant_reply = messages.data[0].content[0].text.value

        # увеличиваем счётчик сообщений
        user.free_messages_used += 1
        db.commit()

    except Exception as e:
        print("Ошибка:", e)
        assistant_reply = "Произошла ошибка. Попробуйте позже."

    db.close()

    send_message(chat_id, assistant_reply)
    return {"ok": True}

def send_message(chat_id, text):
    reply_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(reply_url, json=payload)
