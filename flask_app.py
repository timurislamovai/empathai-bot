import os
import json
import asyncio
from datetime import datetime, timedelta
from flask import Flask, request
from telebot import types
import telebot

from utils import load_text, load_user_data, save_user_data

# Telegram Bot Init
import os

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

# Главное меню + кнопка бесплатного периода
def get_keyboard_for_user(is_new_user):
    keyboard = get_main_menu()
    if is_new_user:
        keyboard.row("🆓 Начать бесплатный период")
    return keyboard

# Асинхронная обработка обновлений
async def handle_update(update):
    message = update.message
    if not message:
        return

    chat_id = message.chat.id
    user_id = str(chat_id)
    message_text = message.text

    user_data = load_user_data(user_id)
    if "registered" not in user_data:
        user_data["registered"] = datetime.utcnow().isoformat()
        user_data["trial_active"] = False
        user_data["messages"] = {}
        save_user_data(user_id, user_data)

    keyboard = get_keyboard_for_user(not user_data.get("trial_active", False))

    if message_text == "/start":
        reply = "Привет! Я EmpathAI — виртуальный помощник. Я помогу тебе справиться с тревогой, сомнениями и мыслями.\n\n🆓 Чтобы начать — нажми кнопку *Начать бесплатный период*."
    elif message_text == "🆓 Начать бесплатный период":
        user_data["trial_active"] = True
        user_data["trial_start"] = datetime.utcnow().isoformat()
        user_data["messages"] = {}
        reply = load_text("texts/trial_info.txt")
    elif message_text == "💳 Купить подписку":
        reply = load_text("texts/subscribe.txt")
    elif message_text == "🔄 Сбросить диалог":
        user_data["messages"] = {}
        reply = load_text("texts/reset.txt")
    elif message_text == "🧠 Инструкция":
        reply = load_text("texts/support.txt")
    elif message_text == "❓ Гид по боту":
        reply = load_text("texts/faq.txt")
    elif message_text == "ℹ️ О Сервисе":
        reply = load_text("texts/info.txt")
    elif message_text == "📜 Пользовательское соглашение":
        reply = load_text("texts/rules.txt")
    else:
        # Проверка пробного периода
        if user_data.get("trial_active", False):
            start_date = datetime.fromisoformat(user_data["trial_start"])
            if datetime.utcnow() - start_date > timedelta(days=FREE_TRIAL_DAYS):
                user_data["trial_active"] = False
                reply = load_text("texts/trial_expired.txt")
                save_user_data(user_id, user_data)
                await bot.send_message(chat_id, reply, reply_markup=keyboard)
                return

            today = datetime.utcnow().strftime("%Y-%m-%d")
            user_data["messages"].setdefault(today, 0)
            if user_data["messages"][today] >= DAILY_MESSAGE_LIMIT:
                reply = load_text("texts/trial_expired.txt")
            else:
                user_data["messages"][today] += 1
                reply = f"✅ Ваше сообщение принято ({user_data['messages'][today]}/{DAILY_MESSAGE_LIMIT})."
        else:
            reply = load_text("texts/trial_expired.txt")

    save_user_data(user_id, user_data)
    await bot.send_message(chat_id, reply, reply_markup=keyboard)

# Webhook обработка
@app.route("/webhook", methods=["POST"])
def webhook():
    update = types.Update.de_json(request.get_json(force=True), bot)
    asyncio.run(handle_update(update))
    return "OK", 200

# Запуск локально или на Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
