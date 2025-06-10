import os
import json
from datetime import datetime, timedelta
from flask import Flask, request
from telebot import types
import telebot

from utils import load_text, load_user_data, save_user_data

# Flask App Init
app = Flask(__name__)

# Telegram Bot Init
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен в переменных окружения")

bot = telebot.TeleBot(TOKEN)

# Константы
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

# Главное меню + кнопка бесплатного периода
def get_keyboard_for_user(is_new_user):
    keyboard = get_main_menu()
    if is_new_user:
        keyboard.row("🆓 Начать бесплатный период")
    return keyboard

# Обработка апдейта
def handle_update(update):
    message = update.message
    if not message:
        return

    chat_id = message.chat.id
    user_id = str(chat_id)
    message_text = message.text

    user_data = load_user_data(user_id)
    if user_id not in user_data:
        # Новый пользователь
        user_data[user_id] = {
            "start_date": datetime.utcnow().isoformat(),
            "messages_sent_today": 0,
            "last_message_date": datetime.utcnow().date().isoformat(),
        }
        save_user_data(user_id, user_data)
        reply = "👋 Привет! Добро пожаловать в EmpathAI.\nНажми кнопку ниже, чтобы начать бесплатный период."
        keyboard = get_keyboard_for_user(is_new_user=True)
        bot.send_message(chat_id, reply, reply_markup=keyboard)
        return

    # Уже есть пользователь
    reply = "🤖 Я тебя слушаю. Напиши свой вопрос или выбери действие из меню."
    keyboard = get_keyboard_for_user(is_new_user=False)
    bot.send_message(chat_id, reply, reply_markup=keyboard)

# Webhook обработка
@app.route("/webhook", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = types.Update.de_json(json_str)
    handle_update(update)
    return "OK", 200

# Локальный запуск
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
