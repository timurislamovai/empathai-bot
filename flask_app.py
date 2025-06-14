import os
import requests
from flask import Flask, request
from telegram import Bot, ReplyKeyboardMarkup, KeyboardButton
from openai import OpenAI
import json

# === Настройки ===
app = Flask(__name__)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")
JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

openai_client = OpenAI(api_key=OPENAI_API_KEY)
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# === Интерфейс главного меню ===
def main_menu():
    buttons = [["🧠 Инструкция", "❓ Гид по боту"], ["📜 Условия пользования", "💳 Купить подписку"]]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# === Работа с JSONBin для хранения thread_id ===
def get_thread_id(user_id):
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
    headers = {"X-Master-Key": JSONBIN_API_KEY}
    response = requests.get(url, headers=headers)
    data = response.json()["record"]
    return data.get(str(user_id))

def save_thread_id(user_id, thread_id):
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
    headers = {
        "X-Master-Key": JSONBIN_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.get(url + "/latest", headers=headers)
    data = response.json()["record"]
    data[str(user_id)] = thread_id
    requests.put(url, headers=headers, json=data)

def reset_thread_id(user_id):
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
    headers = {
        "X-Master-Key": JSONBIN_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.get(url + "/latest", headers=headers)
    data = response.json()["record"]
    data.pop(str(user_id), None)
    requests.put(url, headers=headers, json=data)

# === Чтение текстовых файлов ===
def read_file(name):
    try:
        with open(name, encoding="utf-8") as f:
            return f.read()
    except:
        return "[Файл не найден]"

# === Отправка сообщения через Telegram ===
def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": reply_markup.to_dict() if reply_markup else None
    }
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json=payload)

# === Обращение к OpenAI Assistant ===
def send_to_assistant(user_id, user_input):
    thread_id = get_thread_id(user_id)
    if not thread_id:
        thread = openai_client.beta.threads.create()
        thread_id = thread.id
        save_thread_id(user_id, thread_id)

    openai_client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_input
    )

    run = openai_client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID,
        instructions="Отвечай без Markdown, не используй *, **, --- и ###. Пиши красиво и понятно, как заботливый человек."
    )

    while True:
        status = openai_client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if status.status == "completed":
            break

    messages = openai_client.beta.threads.messages.list(thread_id=thread_id)
    for msg in reversed(messages.data):
        if msg.role == "assistant":
            return msg.content[0].text.value
    return "Извини, я не смог ответить. Попробуй ещё раз."

# === Обработка входящих сообщений ===
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    message = data.get("message")
    if not message:
        return "ok"

    text = message.get("text", "")
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]

    if text == "/start":
        welcome = (
            "Привет, я Ила — твой виртуальный помощник в понимании себя и поиске душевного равновесия\n\n"
            "💙 Я здесь, чтобы поддержать тебя в сложные моменты, помочь разобраться в эмоциях и найти пути к спокойствию.\n"
            "✨ Выберите пункт меню или напишите свой вопрос, чтобы начать общение"
        )
        send_message(chat_id, welcome, reply_markup=main_menu())
        return "ok"

    elif text == "🧠 Инструкция":
        send_message(chat_id, read_file("support.txt"))
        return "ok"
    elif text == "❓ Гид по боту":
        send_message(chat_id, read_file("faq.txt"))
        return "ok"
    elif text == "📜 Условия пользования":
        send_message(chat_id, read_file("rules.txt"))
        return "ok"
    elif text == "💳 Купить подписку":
        send_message(chat_id, read_file("subscribe.txt"))
        return "ok"
    elif text.lower() in ["сброс", "сбросить", "сбросить диалог"]:
        reset_thread_id(user_id)
        send_message(chat_id, read_file("reset.txt"))
        return "ok"

    # Ответ по умолчанию через GPT
    response = send_to_assistant(user_id, text)
    send_message(chat_id, response)
    return "ok"

# === Запуск ===
@app.route("/")
def index():
    return "Бот работает!"

if __name__ == "__main__":
    app.run(debug=True)
