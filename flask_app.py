import os
import json
import requests
from flask import Flask, request, jsonify
from telegram import Bot, Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
import openai

app = Flask(__name__)

# Переменные окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID")
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")

# Инициализация бота
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Папка с текстами
TEXT_FOLDER = "texts"

# Функции для работы с JSONBin.io
def load_history(user_id):
    try:
        response = requests.get(
            f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest",
            headers={"X-Master-Key": JSONBIN_API_KEY}
        )
        response.raise_for_status()
        all_data = response.json().get("record", {})
        user_data = all_data.get(user_id, [])
        if isinstance(user_data, list):
            return user_data
        else:
            print(f"[!] История пользователя {user_id} не список, сбрасываю.")
            return []
    except Exception as e:
        print(f"[!] Ошибка загрузки истории: {e}")
        return []

def save_history(user_id, history):
    try:
        response = requests.get(
            f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest",
            headers={"X-Master-Key": JSONBIN_API_KEY}
        )
        response.raise_for_status()
        all_data = response.json().get("record", {})
        all_data[user_id] = history

        update = requests.put(
            f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}",
            headers={
                "X-Master-Key": JSONBIN_API_KEY,
                "Content-Type": "application/json"
            },
            json={"record": all_data}
        )
        update.raise_for_status()
    except Exception as e:
        print(f"[!] Ошибка сохранения истории: {e}")

def reset_history(user_id):
    save_history(user_id, [])

# Загрузка текстов для меню
def load_text(name):
    try:
        with open(f"{TEXT_FOLDER}/{name}.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Извините, информация временно недоступна."

# Генерация ответа через Open AI
def generate_response(user_id, message_text):
    history = load_history(user_id)
    history.append({"role": "user", "content": message_text})

    openai.api_key = OPENAI_API_KEY
    thread = openai.beta.threads.create()
    thread_id = thread.id

    for msg in history:
        openai.beta.threads.messages.create(
            thread_id=thread_id,
            role=msg["role"],
            content=msg["content"]
        )

    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )

    while True:
        status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if status.status == "completed":
            break
        elif status.status in ["failed", "cancelled", "expired"]:
            return "Извините, произошла ошибка. Попробуйте позже."

    messages = openai.beta.threads.messages.list(thread_id=thread_id)
    reply = ""
    for msg in reversed(messages.data):
        if msg.role == "assistant":
            reply = msg.content[0].text.value
            break

    history.append({"role": "assistant", "content": reply})
    save_history(user_id, history)
    return reply

# Нижнее меню (новые названия кнопок)
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("Инструкция"), KeyboardButton("О Сервисе")],
        [KeyboardButton("Сбросить диалог"), KeyboardButton("Пользовательское соглашение")],
        [KeyboardButton("Гид по боту")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

@app.route(f"/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    if not update or not update.effective_chat:
        return jsonify({"status": "error", "message": "Invalid update"})

    chat_id = str(update.effective_chat.id)
    text = update.message.text.strip() if update.message and update.message.text else ""

    if text == "/start":
        welcome = (
            "Привет! Я Ила — твой виртуальный психолог и наставник по саморазвитию.\n\n"
            "Я здесь, чтобы помочь справляться с тревогой, стрессом и найти ответы на важные вопросы.\n\n"
            "Выбери пункт меню или напиши мне."
        )
        bot.send_message(chat_id=chat_id, text=welcome, reply_markup=main_menu)
        return jsonify({"status": "ok"})

    elif text == "Инструкция":
        bot.send_message(chat_id=chat_id, text=load_text("support"), reply_markup=main_menu)
    elif text == "О Сервисе":
        bot.send_message(chat_id=chat_id, text=load_text("info"), reply_markup=main_menu)
    elif text == "Пользовательское соглашение":
        bot.send_message(chat_id=chat_id, text=load_text("rules"), reply_markup=main_menu)
    elif text == "Гид по боту":
        bot.send_message(chat_id=chat_id, text=load_text("faq"), reply_markup=main_menu)
    elif text == "Сбросить диалог":
        reset_history(chat_id)
        bot.send_message(chat_id=chat_id, text=load_text("reset"), reply_markup=main_menu)
    else:
        answer = generate_response(chat_id, text)
        bot.send_message(chat_id=chat_id, text=answer, reply_markup=main_menu)

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True)
