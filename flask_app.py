import os
import time
import json
import requests
from flask import Flask, request
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Загрузка переменных окружения
load_dotenv()

# Flask-приложение
app = Flask(__name__)

# Переменные окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
JSONBIN_URL = os.getenv("JSONBIN_URL")
JSONBIN_SECRET = os.getenv("JSONBIN_SECRET")

TRIAL_LIMIT = 15
TRIAL_DAYS = 3
TIMEZONE_OFFSET = timedelta(hours=5)

def main_menu():
    return {
        "keyboard": [
            [{"text": "🧠 Инструкция"}, {"text": "❓ Гид по боту"}],
            [{"text": "ℹ️ О Сервисе"}, {"text": "🔄 Сбросить диалог"}],
            [{"text": "📜 Условия пользования"}, {"text": "💳 Купить подписку"}]
        ],
        "resize_keyboard": True
    }

def start_trial_menu():
    return {
        "keyboard": [
            [{"text": "🆓 Начать бесплатный период"}]
        ],
        "resize_keyboard": True
    }

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(url, json=payload)

def get_user_data(user_id):
    headers = {"X-Master-Key": JSONBIN_SECRET}
    res = requests.get(f"{JSONBIN_URL}/{user_id}", headers=headers)
    if res.status_code == 200:
        return res.json().get("record", {})
    return {}

def save_user_data(user_id, data):
    headers = {
        "X-Master-Key": JSONBIN_SECRET,
        "Content-Type": "application/json"
    }
    requests.put(f"{JSONBIN_URL}/{user_id}", headers=headers, data=json.dumps(data))

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = request.get_json()
        handle_update(update)
        return "OK"
    except Exception as e:
        print(f"[ERROR] Webhook exception: {e}")
        return "Internal Server Error", 500

def handle_update(update):
    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    user_id = str(chat_id)

    user_data = get_user_data(user_id)

    if text == "/start":
        if not user_data.get("free_trial_start") and not user_data.get("is_subscribed"):
            welcome_text = (
                "👋 Добро пожаловать в EmpathAI!\n\n"
                "Я твой виртуальный помощник для поддержки, саморазвития и снижения тревожности.\n\n"
                "🆓 Нажми кнопку «Начать бесплатный период», чтобы активировать 3 дня доступа с лимитом 15 сообщений в день."
            )
            send_message(chat_id, welcome_text, reply_markup=start_trial_menu())
        else:
            send_message(chat_id, "С возвращением! Продолжим?", reply_markup=main_menu())
        return

    if text == "🆓 Начать бесплатный период":
        now = datetime.utcnow() + TIMEZONE_OFFSET
        if not user_data.get("free_trial_start"):
            user_data["free_trial_start"] = now.strftime("%Y-%m-%d")
            user_data["last_message_date"] = now.strftime("%Y-%m-%d")
            user_data["messages_today"] = 0
            save_user_data(user_id, user_data)
            send_message(chat_id, "Бесплатный период активирован! Можешь начать общение.", reply_markup=main_menu())
        else:
            send_message(chat_id, "Вы уже активировали бесплатный период.", reply_markup=main_menu())
        return

    if text == "🔄 Сбросить диалог":
        user_data.pop("thread_id", None)
        save_user_data(user_id, user_data)
        if not user_data.get("free_trial_start") and not user_data.get("is_subscribed"):
            send_message(chat_id, "Нажми «Начать бесплатный период», чтобы начать!", reply_markup=start_trial_menu())
        else:
            send_message(chat_id, "Диалог сброшен. Продолжим?", reply_markup=main_menu())
        return

    if text in ["🧠 Инструкция", "❓ Гид по боту", "ℹ️ О Сервисе", "📜 Условия пользования", "💳 Купить подписку"]:
        filename = {
            "🧠 Инструкция": "support",
            "❓ Гид по боту": "faq",
            "ℹ️ О Сервисе": "info",
            "📜 Условия пользования": "rules",
            "💳 Купить подписку": "subscribe"
        }.get(text, "faq")
        try:
            with open(f"texts/{filename}.txt", "r", encoding="utf-8") as f:
                content = f.read()
        except:
            content = "Файл не найден."
        send_message(chat_id, content, reply_markup=main_menu())
        return

    # Проверка пробного периода
    if not user_data.get("is_subscribed"):
        now = datetime.utcnow() + TIMEZONE_OFFSET
        today_str = now.strftime("%Y-%m-%d")

        start_date_str = user_data.get("free_trial_start")
        if not start_date_str:
            send_message(chat_id, "Нажми «Начать бесплатный период», чтобы получить доступ!", reply_markup=start_trial_menu())
            return

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        if (now - start_date).days >= TRIAL_DAYS:
            send_message(chat_id, "⏳ Срок бесплатного периода истёк. 💳 Купить подписку?", reply_markup=main_menu())
            return

        if user_data.get("last_message_date") != today_str:
            user_data["messages_today"] = 0
            user_data["last_message_date"] = today_str

        messages_today = user_data.get("messages_today", 0)
        if messages_today >= TRIAL_LIMIT:
            send_message(chat_id, "🚫 Вы достигли дневного лимита. 💳 Купить подписку?", reply_markup=main_menu())
            return

        user_data["messages_today"] = messages_today + 1
        save_user_data(user_id, user_data)

    # Запрос к OpenAI Assistant API
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "assistants=v2",
        "Content-Type": "application/json"
    }

    thread_id = user_data.get("thread_id")
    if not thread_id:
        res = requests.post("https://api.openai.com/v1/threads", headers=headers)
        if res.status_code == 200:
            thread_id = res.json()["id"]
            user_data["thread_id"] = thread_id
            save_user_data(user_id, user_data)
        else:
            send_message(chat_id, "Ошибка инициализации сессии.", reply_markup=main_menu())
            return

    requests.post(f"https://api.openai.com/v1/threads/{thread_id}/messages", headers=headers, json={
        "role": "user",
        "content": text
    })

    run = requests.post(f"https://api.openai.com/v1/threads/{thread_id}/runs", headers=headers, json={
        "assistant_id": ASSISTANT_ID
    })

    run_id = run.json()["id"]

    for _ in range(20):
        status = requests.get(f"https://api.openai.com/v1/threads/{thread_id}/runs/{run_id}", headers=headers).json()
        if status.get("status") == "completed":
            break
        time.sleep(1)

    messages = requests.get(f"https://api.openai.com/v1/threads/{thread_id}/messages", headers=headers).json()
    reply = messages["data"][0]["content"][0]["text"]["value"]

    send_message(chat_id, reply, reply_markup=main_menu())

if __name__ == "__main__":
    app.run(debug=True)
