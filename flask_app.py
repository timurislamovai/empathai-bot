import os
import json
import asyncio
from flask import Flask, request
from telebot import types
import telebot
from openai import OpenAI
from utils import load_text, load_user_data, save_user_data

# Загрузка переменных окружения
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не установлен")
if not ASSISTANT_ID:
    raise ValueError("OPENAI_ASSISTANT_ID не установлен")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

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

# Доп. кнопка для новых пользователей
def get_keyboard_for_user(is_new_user):
    keyboard = get_main_menu()
    if is_new_user:
        keyboard.row("🆓 Начать бесплатный период")
    return keyboard

# Обработка текстов команд
def process_menu_command(message):
    texts = {
        "🧠 Инструкция": "support",
        "❓ Гид по боту": "faq",
        "ℹ️ О Сервисе": "info",
        "📜 Пользовательское соглашение": "rules",
        "🔄 Сбросить диалог": "reset"
    }
    return load_text(texts.get(message.text))

# Получение ответа от OpenAI Assistant API
async def get_assistant_response(user_id, message_text):
    user_data = load_user_data(user_id)
    thread_id = user_data.get("thread_id")

    if not thread_id:
        thread = client.beta.threads.create()
        thread_id = thread.id
        user_data["thread_id"] = thread_id

    # Добавление сообщения в поток
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message_text
    )

    # Запуск ассистента
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )

    # Ожидание завершения run
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status == "completed":
            break
        elif run_status.status == "failed":
            return "Произошла ошибка при обработке запроса. Попробуй позже."
        await asyncio.sleep(1)

    # Получение ответа
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    for msg in reversed(messages.data):
        if msg.role == "assistant":
            user_data["thread_id"] = thread_id
            save_user_data(user_id, user_data)
            return msg.content[0].text.value

    return "Не удалось получить ответ от ассистента."

# Асинхронная обработка сообщения
async def handle_update(update):
    message = update.message
    if not message or not message.text:
        return

    user_id = str(message.chat.id)
    user_data = load_user_data(user_id)
    chat_id = message.chat.id
    message_text = message.text.strip()

    if message_text in ["🧠 Инструкция", "❓ Гид по боту", "ℹ️ О Сервисе", "📜 Пользовательское соглашение", "🔄 Сбросить диалог"]:
        reply = process_menu_command(message)
    elif message_text == "🆓 Начать бесплатный период":
        reply = "Бесплатный период активирован! Теперь вы можете задать до 15 сообщений в течение 7 дней."
    elif message_text == "💳 Купить подписку":
        reply = "Для покупки подписки перейдите по ссылке: https://ваш-сайт/оплата"
    else:
        reply = await get_assistant_response(user_id, message_text)

    keyboard = get_keyboard_for_user(is_new_user="thread_id" not in user_data)
    bot.send_message(chat_id, reply, reply_markup=keyboard)

# Обработка webhook'а от Telegram
@app.route("/webhook", methods=["POST"])
def webhook():
    update = types.Update.de_json(request.get_json(force=True))
    asyncio.run(handle_update(update))
    return "OK", 200

# Локальный запуск
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
