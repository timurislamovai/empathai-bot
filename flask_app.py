import os
import time
import json
import requests
from flask import Flask, request
from dotenv import load_dotenv

from db import SessionLocal
from models import User

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

# === Главное меню ===
def main_menu():
    return {
        "keyboard": [
            [{"text": "🧠 Инструкция"}, {"text": "❓ Гид по боту"}],
            [{"text": "🔄 Сбросить диалог"}, {"text": "💳 Купить подписку"}],
            [{"text": "📜 Условия пользования"}]
        ],
        "resize_keyboard": True
    }

# === Работа с базой данных ===
def get_user(chat_id):
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=str(chat_id)).first()
    session.close()
    return user

def save_user(chat_id, thread_id):
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=str(chat_id)).first()
    if not user:
        user = User(telegram_id=str(chat_id), thread_id=thread_id)
        session.add(user)
    else:
        user.thread_id = thread_id
    session.commit()
    session.close()

def reset_thread(chat_id):
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=str(chat_id)).first()
    if user:
        user.thread_id = None
        session.commit()
    session.close()

# === Отправка сообщений в Telegram ===
def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"[ERROR] Telegram send failed: {response.status_code} {response.text}")

# === Webhook обработчик ===
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

    if text == "/start":
        welcome_text = (
            "👋 Добро пожаловать в EmpathAI!\n\n"
            "Я твой виртуальный помощник для поддержки, саморазвития и снижения тревожности.\n\n"
            "📋 Выбери пункт из меню, чтобы начать общение."
        )
        send_message(chat_id, welcome_text, reply_markup=main_menu())
        return

    if text == "🔄 Сбросить диалог":
        reset_thread(chat_id)
        send_message(chat_id, "Диалог сброшен. Начнём заново?", reply_markup=main_menu())
        return

    if text in ["🧠 Инструкция", "❓ Гид по боту", "💳 Купить подписку", "📜 Условия пользования"]:
        filename = {
            "🧠 Инструкция": "support",
            "❓ Гид по боту": "faq",
            "💳 Купить подписку": "subscribe",
            "📜 Условия пользования": "rules"
        }.get(text, "faq")
        try:
            with open(f"texts/{filename}.txt", "r", encoding="utf-8") as f:
                content = f.read()
        except:
            content = "Файл не найден."
        send_message(chat_id, content, reply_markup=main_menu())
        return

    # GPT-переписка
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "assistants=v2",
        "Content-Type": "application/json"
    }

    user = get_user(chat_id)
    thread_id = user.thread_id if user and user.thread_id else None

    if not thread_id:
        thread_res = requests.post("https://api.openai.com/v1/threads", headers=headers)
        if thread_res.status_code != 200:
            send_message(chat_id, "❌ Ошибка инициализации сессии.", reply_markup=main_menu())
            return
        thread_id = thread_res.json()["id"]
        save_user(chat_id, thread_id)

    msg_payload = {"role": "user", "content": text}
    requests.post(
        f"https://api.openai.com/v1/threads/{thread_id}/messages",
        headers=headers,
        json=msg_payload
    )

    run_payload = {"assistant_id": ASSISTANT_ID}
    run_res = requests.post(
        f"https://api.openai.com/v1/threads/{thread_id}/runs",
        headers=headers,
        json=run_payload
    )

    if run_res.status_code != 200:
        send_message(chat_id, "❌ Ошибка запуска AI-сессии.", reply_markup=main_menu())
        return

    run_id = run_res.json()["id"]

    for _ in range(30):
        time.sleep(1)
        check = requests.get(
            f"https://api.openai.com/v1/threads/{thread_id}/runs/{run_id}",
            headers=headers
        )
        status = check.json().get("status")
        if status == "completed":
            break
    else:
        send_message(chat_id, "⏳ Превышено время ожидания ответа.", reply_markup=main_menu())
        return

    messages_res = requests.get(
    f"https://api.openai.com/v1/threads/{thread_id}/messages",
    headers=headers
)

if messages_res.status_code != 200:
      send_message(chat_id, "❌ Ошибка получения ответа.", reply_markup=main_menu())
      return

messages = messages_res.json().get("data", [])
for msg in reversed(messages):
    if msg["role"] == "assistant":
        parts = msg.get("content", [])
        full_text = ""
        for part in parts:
            if part["type"] == "text":
                full_text += part["text"]["value"]
        send_message(chat_id, full_text.strip(), reply_markup=main_menu())
        break
