import os
import json
import asyncio
from datetime import datetime, timedelta
from flask import Flask, request
from telebot import types
import telebot
import openai

from utils import load_text, load_user_data, save_user_data

# Инициализация Flask
app = Flask(__name__)

# Константы и ключи
openai.api_key = os.environ.get("OPENAI_API_KEY")
ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID")
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен в переменных окружения")

bot = telebot.TeleBot(TOKEN)

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


# Асинхронная обработка сообщений
async def handle_update(update):
    message = update.message
    if not message:
        return

    chat_id = message.chat.id
    user_id = str(chat_id)
    message_text = message.text.strip()

    user_data = load_user_data(user_id)
    thread_id = user_data.get("thread_id")

    if message_text == "/start" or message_text == "🆓 Начать бесплатный период":
        welcome_text = (
            "👋 Добро пожаловать в EmpathAI — твоего личного психолога и наставника.\n"
            "Бесплатный пробный период активен. Задай свой первый вопрос."
        )
        bot.send_message(chat_id, welcome_text, reply_markup=get_main_menu())
        return

    if message_text in ["🧠 Инструкция", "❓ Гид по боту", "ℹ️ О Сервисе", "📜 Пользовательское соглашение", "🔄 Сбросить диалог"]:
        filename_map = {
            "🧠 Инструкция": "support",
            "❓ Гид по боту": "faq",
            "ℹ️ О Сервисе": "info",
            "📜 Пользовательское соглашение": "rules",
            "🔄 Сбросить диалог": "reset"
        }
        filename = filename_map.get(message_text)

        if filename == "reset":
            user_data.pop("thread_id", None)
            save_user_data(user_id, user_data)

        text = load_text(filename)
        bot.send_message(chat_id, text, reply_markup=get_main_menu())
        return

    if not thread_id:
        thread = openai.beta.threads.create()
        thread_id = thread.id
        user_data["thread_id"] = thread_id
        save_user_data(user_id, user_data)

    openai.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message_text
    )

    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )

    while True:
        run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status == "completed":
            break
        elif run_status.status in ("failed", "cancelled", "expired"):
            bot.send_message(chat_id, "❌ Произошла ошибка. Попробуй позже.")
            return
        await asyncio.sleep(1)

    messages = openai.beta.threads.messages.list(thread_id=thread_id)
    for msg in reversed(messages.data):
        if msg.role == "assistant":
            answer = msg.content[0].text.value
            break
    else:
        answer = "🤖 Не удалось получить ответ. Попробуй позже."

    await bot.send_message(chat_id, answer, reply_markup=get_main_menu())


# Webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    update = types.Update.de_json(request.get_json(force=True))
    asyncio.run(handle_update(update))
    return "OK", 200

# Локальный запуск
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
