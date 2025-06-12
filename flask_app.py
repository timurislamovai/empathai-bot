import os
import json
import asyncio
from datetime import datetime, timedelta
from flask import Flask, request
import requests

from telegram import Bot, ReplyKeyboardMarkup

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
JSONBIN_URL = os.getenv("JSONBIN_URL")
JSONBIN_SECRET = os.getenv("JSONBIN_SECRET")
TIMEZONE_OFFSET = timedelta(hours=5)  # Например, для UTC+5

bot = Bot(token=TELEGRAM_BOT_TOKEN)

MAIN_MENU = ReplyKeyboardMarkup([
    ["🧠 Инструкция", "❓ Гид по боту"],
    ["ℹ️ О Сервисе", "🔄 Сбросить диалог"],
    ["📜 Условия пользования", "💳 Купить подписку"]
], resize_keyboard=True)

TRIAL_LIMIT = 10  # лимит сообщений в день
TRIAL_DAYS = 3

async def send_message(chat_id, text, reply_markup=None):
    await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

def get_user_data(user_id):
    headers = {"X-Master-Key": JSONBIN_SECRET}
    res = requests.get(f"{JSONBIN_URL}/{user_id}", headers=headers)
    if res.status_code == 200:
        return res.json().get("record", {})
    return {}

def save_user_data(user_id, data):
    headers = {
        "X-Master-Key": JSONBIN_SECRET,
        "Content-Type": "application/json"
    }
    requests.put(f"{JSONBIN_URL}/{user_id}", headers=headers, data=json.dumps(data))

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    asyncio.run(handle_update(update))
    return "OK"

async def handle_update(update):
    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    user_id = str(chat_id)

    if text == "/start":
        user_data = get_user_data(user_id)
        if not user_data.get("free_trial_start") and not user_data.get("is_subscribed"):
            keyboard = ReplyKeyboardMarkup([["🆓 Начать бесплатный период"]], resize_keyboard=True)
            await send_message(chat_id, "Добро пожаловать! Хотите начать бесплатный период на 3 дня?", keyboard)
        else:
            await send_message(chat_id, "С возвращением!", MAIN_MENU)
        return

    if text == "🆓 Начать бесплатный период":
        now = datetime.utcnow() + TIMEZONE_OFFSET
        user_data = get_user_data(user_id)
        if not user_data.get("free_trial_start"):
            user_data["free_trial_start"] = now.strftime("%Y-%m-%d")
            user_data["last_message_date"] = now.strftime("%Y-%m-%d")
            user_data["messages_today"] = 0
            save_user_data(user_id, user_data)
            await send_message(chat_id, "Бесплатный период активирован!", MAIN_MENU)
        else:
            await send_message(chat_id, "Вы уже активировали бесплатный период.", MAIN_MENU)
        return

    # Обработка кнопок меню
    if text in ["🧠 Инструкция", "❓ Гид по боту", "ℹ️ О Сервисе", "📜 Условия пользования", "💳 Купить подписку"]:
        filename = {
            "🧠 Инструкция": "support",
            "❓ Гид по боту": "faq",
            "ℹ️ О Сервисе": "info",
            "📜 Условия пользования": "rules",
            "💳 Купить подписку": "subscribe"
        }.get(text, "faq")
        try:
            with open(f"texts/{filename}.txt", "r", encoding="utf-8") as f:
                content = f.read()
        except:
            content = "Файл не найден."
        await send_message(chat_id, content, MAIN_MENU)
        return

    # Проверка лимита сообщений
    user_data = get_user_data(user_id)
    if user_data.get("is_subscribed"):
        trial_active = True
    else:
        now = datetime.utcnow() + TIMEZONE_OFFSET
        today_str = now.strftime("%Y-%m-%d")

        start_date_str = user_data.get("free_trial_start")
        if not start_date_str:
            await send_message(chat_id, "Нажми 🆓 Начать бесплатный период, чтобы получить 3 дня и 10 сообщений в день!", MAIN_MENU)
            return

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        if (now - start_date).days >= TRIAL_DAYS:
            await send_message(chat_id, "Срок бесплатного периода истёк. 💳 Купить подписку?", MAIN_MENU)
            return

        if user_data.get("last_message_date") != today_str:
            user_data["messages_today"] = 0
            user_data["last_message_date"] = today_str
            await send_message(chat_id, f"Вы используете бесплатную версию. Вам доступно {TRIAL_LIMIT} сообщений в день. Лимит обновляется ежедневно.\n", MAIN_MENU)

        messages_today = user_data.get("messages_today", 0)
        if messages_today >= TRIAL_LIMIT:
            await send_message(chat_id, "Вы достигли дневного лимита. 💳 Купить подписку?", MAIN_MENU)
            return

        user_data["messages_today"] = messages_today + 1
        save_user_data(user_id, user_data)
        remaining = TRIAL_LIMIT - user_data["messages_today"]
        await send_message(chat_id, f"Осталось {remaining} сообщений сегодня.")

    # Отправка запроса в OpenAI
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "assistants=v2",
        "Content-Type": "application/json"
    }

    thread_id = user_data.get("thread_id")
    if not thread_id:
        res = requests.post("https://api.openai.com/v1/threads", headers=headers)
        if res.status_code == 200:
            thread_id = res.json()["id"]
            user_data["thread_id"] = thread_id
            save_user_data(user_id, user_data)
        else:
            await send_message(chat_id, "Ошибка инициализации сессии.", MAIN_MENU)
            return

    requests.post(f"https://api.openai.com/v1/threads/{thread_id}/messages", headers=headers, json={
        "role": "user",
        "content": text
    })

    run = requests.post(f"https://api.openai.com/v1/threads/{thread_id}/runs", headers=headers, json={
        "assistant_id": ASSISTANT_ID
    })

    run_id = run.json()["id"]

    # Ждём завершения
    for _ in range(20):
        status = requests.get(f"https://api.openai.com/v1/threads/{thread_id}/runs/{run_id}", headers=headers).json()
        if status.get("status") == "completed":
            break
        await asyncio.sleep(1)

    messages = requests.get(f"https://api.openai.com/v1/threads/{thread_id}/messages", headers=headers).json()
    reply = messages["data"][0]["content"][0]["text"]["value"]

    await send_message(chat_id, reply, MAIN_MENU)

if __name__ == "__main__":
    app.run(debug=True)
