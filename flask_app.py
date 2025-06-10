# flask_app.py с сохранением оригинального меню и добавлением пробного периода и подписки
import os
import json
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from telegram import Bot, ReplyKeyboardMarkup, KeyboardButton
import openai
import time

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID")
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
TEXT_FOLDER = "texts"

TRIAL_DAYS = 7
TRIAL_DAILY_LIMIT = 15

def load_all_data():
    try:
        response = requests.get(
            f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest",
            headers={"X-Master-Key": JSONBIN_API_KEY}
        )
        response.raise_for_status()
        return response.json().get("record", {})
    except Exception as e:
        print(f"[!] Ошибка загрузки данных: {e}")
        return {}

def save_all_data(data):
    try:
        response = requests.put(
            f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}",
            headers={
                "X-Master-Key": JSONBIN_API_KEY,
                "Content-Type": "application/json"
            },
            json={"record": data}
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"[!] Ошибка сохранения: {e}")
        return False

def load_user(user_id):
    data = load_all_data()
    return data.get(user_id, None), data

def save_user(user_id, user_data, full_data):
    full_data[user_id] = user_data
    return save_all_data(full_data)

def check_access(user_id):
    user_data, all_data = load_user(user_id)
    today = datetime.utcnow().date().isoformat()
    now = datetime.utcnow()

    if not user_data:
        user_data = {
            "history": [],
            "start_date": today,
            "last_date": today,
            "daily_count": 0,
            "subscription_status": "trial_pending"
        }

    if user_data.get("subscription_status") == "premium":
        return True, user_data, all_data

    if user_data.get("subscription_status") != "trial":
        return False, user_data, all_data

    start_date = datetime.fromisoformat(user_data["start_date"])
    if (now - start_date).days >= TRIAL_DAYS:
        return False, user_data, all_data

    if user_data["last_date"] != today:
        user_data["last_date"] = today
        user_data["daily_count"] = 0

    if user_data["daily_count"] >= TRIAL_DAILY_LIMIT:
        return False, user_data, all_data

    return True, user_data, all_data

def update_history(user_data, message):
    user_data["history"].append(message)
    user_data["history"] = user_data["history"][-10:]
    user_data["daily_count"] += 1
    return user_data

def load_text(name):
    try:
        with open(f"{TEXT_FOLDER}/{name}.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Информация временно недоступна."

def generate_response(user_id, message_text, user_data):
    if not message_text.strip():
        return "Пожалуйста, напиши что-нибудь 😊", user_data

    user_data = update_history(user_data, {"role": "user", "content": message_text[:2000]})
    openai.api_key = OPENAI_API_KEY

    try:
        thread = openai.beta.threads.create(messages=user_data["history"])
    except Exception as e:
        print(f"[!] Ошибка создания потока: {e}")
        return "Ошибка создания диалога. Попробуй ещё раз позже.", user_data

    try:
        run = openai.beta.threads.runs.create(thread_id=thread.id, assistant_id=ASSISTANT_ID)
        max_attempts = 10
        attempts = 0
        while attempts < max_attempts:
            run_status = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run_status.status == "completed":
                break
            time.sleep(1)
            attempts += 1

        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        reply = messages.data[0].content[0].text.value
        user_data = update_history(user_data, {"role": "assistant", "content": reply})
        return reply, user_data
    except Exception as e:
        print(f"[!] Ошибка OpenAI: {e}")
        return "Произошла ошибка при обращении к GPT.", user_data

@app.route("/", methods=["GET"])
def home():
    return "EmpathAI работает и ожидает Telegram-запросов."

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    chat_id = update["message"]["chat"]["id"]
    user_id = str(chat_id)
    message_text = update["message"].get("text", "")

    user_data, all_data = load_user(user_id)

    keyboard_buttons = [
        [KeyboardButton("🧠 Инструкция"), KeyboardButton("ℹ️ О Сервисе")],
        [KeyboardButton("📜 Пользовательское соглашение"), KeyboardButton("❓ Гид по боту")],
        [KeyboardButton("🔄 Сбросить диалог")]
    ]

    if not user_data or user_data.get("subscription_status") in [None, "trial_pending"]:
        keyboard_buttons.append([KeyboardButton("🆓 Начать бесплатный период")])
    keyboard_buttons.append([KeyboardButton("💳 Купить подписку")])

    keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True
    )

    if message_text == "/start":
        welcome = load_text("start")
        bot.send_message(chat_id=chat_id, text=welcome, reply_markup=keyboard)
        return jsonify(success=True)

    elif message_text == "🧠 Инструкция":
        bot.send_message(chat_id=chat_id, text=load_text("support"), reply_markup=keyboard)
    elif message_text == "ℹ️ О Сервисе":
        bot.send_message(chat_id=chat_id, text=load_text("info"), reply_markup=keyboard)
    elif message_text == "📜 Пользовательское соглашение":
        bot.send_message(chat_id=chat_id, text=load_text("rules"), reply_markup=keyboard)
    elif message_text == "❓ Гид по боту":
        bot.send_message(chat_id=chat_id, text=load_text("faq"), reply_markup=keyboard)
    elif message_text == "🔄 Сбросить диалог":
        if user_data:
            user_data["history"] = []
            user_data["daily_count"] = 0
            save_user(user_id, user_data, all_data)
        bot.send_message(chat_id=chat_id, text="🔄 История диалога сброшена! Бот начинает новый разговор, но твои прошлые сообщения остаются видимыми. Теперь можешь задавать свежие вопросы! 😊", reply_markup=keyboard)
    elif message_text == "🆓 Начать бесплатный период":
        if not user_data:
            user_data = {
                "history": [],
                "start_date": datetime.utcnow().date().isoformat(),
                "last_date": datetime.utcnow().date().isoformat(),
                "daily_count": 0,
                "subscription_status": "trial"
            }
        else:
            user_data["subscription_status"] = "trial"
            user_data["start_date"] = datetime.utcnow().date().isoformat()
            user_data["last_date"] = datetime.utcnow().date().isoformat()
            user_data["daily_count"] = 0

        save_user(user_id, user_data, all_data)
        bot.send_message(chat_id=chat_id, text=load_text("trial_info"), reply_markup=keyboard)

    elif message_text == "💳 Купить подписку":
        bot.send_message(chat_id=chat_id, text=load_text("subscribe"), reply_markup=keyboard)
    else:
        access_granted, user_data, all_data = check_access(user_id)
        if not access_granted:
            bot.send_message(chat_id=chat_id, text=load_text("trial_expired"), reply_markup=keyboard)
        else:
            reply, user_data = generate_response(user_id, message_text, user_data)

