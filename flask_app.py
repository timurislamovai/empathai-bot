import os
import time
import openai
import json
import requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

openai.api_key = OPENAI_API_KEY
client = openai

# 🧼 Очистка Markdown из ответов
def clean_markdown(text):
    import re
    text = re.sub(r"[\\*_`>#-]", "", text)  # убираем markdown
    text = re.sub(r"\n{3,}", "\n\n", text)   # убираем лишние переносы
    return text.strip()

# 📎 Основное меню
def main_menu():
    return {
        "keyboard": [
            ["🧠 Инструкция", "❓ Гид по боту"],
            ["📜 Условия пользования", "💳 Купить подписку"],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

# 📤 Отправка сообщения в Telegram
def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": json.dumps(reply_markup) if reply_markup else None,
    }
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", data=payload)

# 🔁 Обработка обновлений
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" not in data:
        return "ok"

    message = data["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if text == "/start":
        welcome_text = "Привет! Я EmpathAI — твой виртуальный помощник. Задай мне любой вопрос или выбери пункт из меню."
        send_message(chat_id, welcome_text, reply_markup=main_menu())
        return "ok"

    elif text in ["🧠 Инструкция", "❓ Гид по боту", "📜 Условия пользования", "💳 Купить подписку"]:
        static_replies = {
            "🧠 Инструкция": "Здесь будет инструкция по использованию бота.",
            "❓ Гид по боту": "Вот как работает бот: напиши вопрос — получи ответ.",
            "📜 Условия пользования": "Пользуясь ботом, вы соглашаетесь с условиями использования.",
            "💳 Купить подписку": "Подписка откроет доступ к расширенным функциям. Скоро будет доступна.",
        }
        send_message(chat_id, static_replies[text], reply_markup=main_menu())
        return "ok"

    # 🧠 Интеграция с GPT Assistant
    thread = client.beta.threads.create()
    thread_id = thread.id

    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=text
    )

    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )

    # ⏱ Ждём ответа OpenAI с таймаутом
    timeout = 10  # секунд
    start_time = time.time()
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status == "completed":
            break
        if time.time() - start_time > timeout:
            send_message(chat_id, "Извините, сейчас я не могу ответить. Попробуйте позже.", reply_markup=main_menu())
            return "timeout"
        time.sleep(0.5)

    messages = client.beta.threads.messages.list(thread_id=thread_id)
    assistant_reply = messages.data[0].content[0].text.value

    # 🧹 Очистка и отправка
    cleaned_reply = clean_markdown(assistant_reply)
    send_message(chat_id, cleaned_reply, reply_markup=main_menu())

    return "ok"

# 🖥 Проверочный маршрут для Render
@app.route("/", methods=["GET"])
def index():
    return "EmpathAI Telegram Bot is running!"
