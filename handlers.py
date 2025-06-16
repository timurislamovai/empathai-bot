import requests
from config import TELEGRAM_TOKEN, BASE_URL
from models import get_user_by_telegram_id, create_user, update_user_thread_id, increment_message_count, reset_user_thread
from openai_api import send_to_openai
from database import SessionLocal

FREE_MESSAGES_LIMIT = 50

def send_message(chat_id, text, show_menu=False):
    reply_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    if show_menu:
        payload["reply_markup"] = {
            "keyboard": [
                [{"text": "Личный кабинет"}, {"text": "Гид по боту"}],
                [{"text": "Сбросить диалог"}, {"text": "Купить подписку"}]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }

    requests.post(reply_url, json=payload)

async def handle_update(update):
    message = update.get("message")
    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    user_message = message.get("text", "")

    db = SessionLocal()
    user = get_user_by_telegram_id(db, chat_id)

    if not user:
        user = create_user(db, chat_id)

    if user_message.lower() == "сбросить диалог":
        reset_user_thread(db, user)
        send_message(chat_id, "🗑 Диалог очищен. Можем начать сначала 😊", show_menu=True)
        db.close()
        return {"ok": True}

    if user_message.lower() == "личный кабинет":
        remaining = max(0, FREE_MESSAGES_LIMIT - user.free_messages_used)
        try:
            with open("texts/profile.txt", "r", encoding="utf-8") as f:
                text = f.read()
            text = text.replace("{remaining}", str(remaining)).replace("{limit}", str(FREE_MESSAGES_LIMIT))
        except Exception:
            text = f"👤 Осталось бесплатных сообщений: {remaining} из {FREE_MESSAGES_LIMIT}"
        send_message(chat_id, text, show_menu=True)
        db.close()
        return {"ok": True}

    if user_message.lower() == "гид по боту":
        try:
            with open("texts/guide.txt", "r", encoding="utf-8") as f:
                guide_text = f.read()
        except Exception:
            guide_text = "📘 Гид по боту недоступен."
        send_message(chat_id, guide_text, show_menu=True)
        db.close()
        return {"ok": True}

    if user_message.lower() == "купить подписку":
        try:
            with open("texts/subscribe.txt", "r", encoding="utf-8") as f:
                sub_text = f.read()
        except Exception:
            sub_text = "💳 Подписка временно недоступна."
        send_message(chat_id, sub_text, show_menu=True)
        db.close()
        return {"ok": True}

    if user.free_messages_used >= FREE_MESSAGES_LIMIT:
        send_message(chat_id, "🚫 Лимит бесплатных сообщений исчерпан. Купите подписку, чтобы продолжить.", show_menu=True)
        db.close()
        return {"ok": True}

    # Отправка сообщения в OpenAI
    reply = send_to_openai(user, user_message)
    send_message(chat_id, reply, show_menu=True)

    # Обновляем счётчики и thread_id
    increment_message_count(db, user)
    update_user_thread_id(db, user)
    db.close()

    return {"ok": True}

async def setup_webhook():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook"
    data = {"url": f"{BASE_URL}/webhook"}
    response = requests.post(url, json=data)
    print("✅ Установлен webhook:", response.json())
