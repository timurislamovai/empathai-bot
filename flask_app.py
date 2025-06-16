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


# === Основная логика обновлений ===
def handle_update(update):
    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    # Команда /start
    if text == "/start":
        welcome_text = (
            "👋 Добро пожаловать в EmpathAI!\n\n"
            "Я твой виртуальный помощник для поддержки, саморазвития и снижения тревожности.\n\n"
            "📋 Выбери пункт из меню, чтобы начать общение."
        )
        send_message(chat_id, welcome_text, reply_markup=main_menu())
        return

    # Сброс диалога
    if text == "🔄 Сбросить диалог":
        reset_thread(chat_id)
        send_message(chat_id, "Диалог сброшен. Начнём заново?", reply_markup=main_menu())
        return

    # Меню-файлы
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
        except FileNotFoundError:
            content = "Файл не найден."
        send_message(chat_id, content, reply_markup=main_menu())
        return

    # GPT-переписка через Assistant API
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "assistants=v2",
        "Content-Type": "application/json"
    }

    user = get_user(chat_id)
    thread_id = user.thread_id if user and user.thread_id else None

    # Если нет активной сессии — создаём новую
    if not thread_id:
        thread_res = requests.post("https://api.openai.com/v1/threads", headers=headers)
        if thread_res.status_code != 200:
            send_message(chat_id, "❌ Ошибка инициализации сессии.", reply_markup=main_menu())
            return
        thread_id = thread_res.json().get("id"
