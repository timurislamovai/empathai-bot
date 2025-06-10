import os
import json
import asyncio
from datetime import datetime, timedelta
from flask import Flask, request
from telebot import types
import telebot

from utils import load_text, load_user_data, save_user_data

# Flask app
app = Flask(__name__)

# Telegram Bot Init
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен в переменных окружения")

bot = telebot.TeleBot(TOKEN)

# Constants
FREE_TRIAL_DAYS = 7
DAILY_MESSAGE_LIMIT = 15

# Главное меню
def get_main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("🧠 Инструкция", "❓ Гид по боту")
    keyboard.row("ℹ️ О Сервисе", "📜 Пользовательское соглашение")
    keyboard.row("🔄 Сбросить диалог")
    keyboard.row("💳 Купить подписку")
    return keyboard

def get_keyboard_for_user(is_new_user):
    keyboard = get_main_menu()
    if is_new_user:
        keyboard.row("🆓 Начать бесплатный период")
    return keyboard

# Обработка обновлений
async def handle_update(update):
    message = update.message
    if not message or not message.text:
        return

    chat_id = message.chat.id
    user_id = str(chat_id)
    message_text = message.text.strip()

    user_data = load_user_data(user_id)
    is_new_user = not user_data

    keyboard = get_keyboard_for_user(is_new_user)

    # Обработка кнопок
    if message_text == "/start" or message_text == "🆓 Начать бесплатный период":
        user_data = {
            "start_date": datetime.utcnow().isoformat(),
            "messages_sent": 0
        }
        save_user_data(user_id, user_data)
        reply = (
            "👋 Привет! Добро пожаловать в EmpathAI — твоего личного помощника в трудные моменты.\n\n"
            "🧠 Я готов выслушать, поддержать и помочь тебе разобраться в себе.\n"
            "Можешь задать вопрос или выбрать действие из меню."
        )
    elif message_text == "🧠 Инструкция":
        reply = load_text("support")
    elif message_text == "❓ Гид по боту":
        reply = load_text("faq")
    elif message_text == "ℹ️ О Сервисе":
        reply = load_text("info")
    elif message_text == "📜 Пользовательское соглашение":
        reply = load_text("rules")
    elif message_text == "🔄 Сбросить диалог":
        save_user_data(user_id, {})
        reply = load_text("reset")
    elif message_text == "💳 Купить подписку":
        reply = "💳 Возможности подписки появятся скоро. Следи за обновлениями!"
    else:
        reply = "🤖 Я тебя слушаю. Напиши свой вопрос или выбери действие из меню."

    await asyncio.to_thread(bot.send_message, chat_id, reply, reply_markup=keyboard)

# Webhook обработка
@app.route("/webhook", methods=["POST"])
def webhook():
    update = types.Update.de_json(request.get_json(force=True))
    asyncio.run(handle_update(update))
    return "OK", 200

# Запуск локально или на Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
