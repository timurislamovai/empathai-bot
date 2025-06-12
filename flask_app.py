import os
import json
import asyncio
from flask import Flask, request
from telebot import types
import telebot
import requests

# 🔍 Отладочный вывод
print("DEBUG: TELEGRAM_BOT_TOKEN =", os.getenv("TELEGRAM_BOT_TOKEN"))
print("DEBUG: OPENAI_API_KEY =", os.getenv("OPENAI_API_KEY"))
print("DEBUG: ASSISTANT_ID =", os.getenv("ASSISTANT_ID"))
print("DEBUG: JSONBIN_API_KEY =", os.getenv("JSONBIN_API_KEY"))
print("DEBUG: JSONBIN_BIN_ID =", os.getenv("JSONBIN_BIN_ID"))

# 💥 Проверка обязательных переменных
if not all([
    os.getenv("TELEGRAM_BOT_TOKEN"),
    os.getenv("OPENAI_API_KEY"),
    os.getenv("ASSISTANT_ID"),
    os.getenv("JSONBIN_API_KEY"),
    os.getenv("JSONBIN_BIN_ID")
]):
    raise ValueError("❌ Одно или несколько обязательных значений переменных окружения не заданы.")

# Инициализация Flask и бота
app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")
JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# 📱 Клавиатура
def get_main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("🧠 Инструкция", "❓ Гид по боту")
    keyboard.row("ℹ️ О Сервисе", "📜 Пользовательское соглашение")
    keyboard.row("🔄 Сбросить диалог", "💳 Купить подписку")
    return keyboard

# 📂 Работа с JSONBin
def load_user_data():
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
    headers = {"X-Master-Key": JSONBIN_API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("record", {})
    return {}

def save_user_data(data):
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
    headers = {
        "Content-Type": "application/json",
        "X-Master-Key": JSONBIN_API_KEY,
        "X-Bin-Versioning": "false"
    }
    requests.put(url, headers=headers, json=data)

# 🤖 Асинхронная обработка
async def handle_update(update):
    message = update.message
    if not message:
        return

    chat_id = message.chat.id
    user_id = str(chat_id)
    text = message.text.strip()

    user_data = load_user_data()
    user_entry = user_data.get(user_id, {"start_date": None, "used_messages": 0})

    # 🔘 Обработка кнопок
    if text == "🔄 Сбросить диалог":
        user_entry["thread_id"] = None
        await send_message(chat_id, "Диалог сброшен. Начните новый запрос.", get_main_menu())
        user_data[user_id] = user_entry
        save_user_data(user_data)
        return
        
if text in ["🧠 Инструкция", "❓ Гид по боту", "ℹ️ О Сервисе", "📜 Пользовательское соглашение", "💳 Купить подписку"]:
    filename = {
        "🧠 Инструкция": "support",
        "❓ Гид по боту": "faq",
        "ℹ️ О Сервисе": "info",
        "📜 Пользовательское соглашение": "rules",
        "💳 Купить подписку": "subscribe"
    }.get(text, "faq")

    try:
        with open(f"texts/{filename}.txt", "r", encoding="utf-8") as f:
            content = f.read()
    except:
        content = "Файл не найден."

    await send_message(chat_id, content, get_main_menu())
    return


    # 🧠 OpenAI (Assistant API)
    thread_id = user_entry.get("thread_id")

    if not thread_id:
        r = requests.post("https://api.openai.com/v1/threads", headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "assistants=v2"
        })

        if r.status_code != 200:
            print("❌ Ошибка создания thread:", r.status_code, r.text)
            await send_message(chat_id, "Ошибка создания диалога. Попробуйте позже.", get_main_menu())
            return

        thread_json = r.json()
        thread_id = thread_json.get("id")
        if not thread_id:
            print("❌ Thread без ID:", thread_json)
            await send_message(chat_id, "Не удалось создать диалог.", get_main_menu())
            return

        user_entry["thread_id"] = thread_id

    # 📩 Отправка запроса
    requests.post(
        f"https://api.openai.com/v1/threads/{thread_id}/messages",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "assistants=v2",
            "Content-Type": "application/json"
        },
        json={"role": "user", "content": text}
    )

    run_resp = requests.post(
        f"https://api.openai.com/v1/threads/{thread_id}/runs",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "assistants=v2",
            "Content-Type": "application/json"
        },
        json={"assistant_id": ASSISTANT_ID}
    )

    run_id = run_resp.json()["id"]

    # ⏳ Ожидание завершения
    status = "in_progress"
    while status in ["queued", "in_progress"]:
        await asyncio.sleep(1)
        r = requests.get(
            f"https://api.openai.com/v1/threads/{thread_id}/runs/{run_id}",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "assistants=v2"
            }
        )
        status = r.json()["status"]

    # 📥 Получение ответа
    messages_resp = requests.get(
        f"https://api.openai.com/v1/threads/{thread_id}/messages",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "assistants=v2"
        }
    )

    last_message = messages_resp.json()["data"][0]["content"][0]["text"]["value"]
    await send_message(chat_id, last_message, get_main_menu())

    # 💾 Сохранение
    user_data[user_id] = user_entry
    save_user_data(user_data)

# 📤 Отправка сообщения
async def send_message(chat_id, text, keyboard=None):
    bot.send_message(chat_id, text, reply_markup=keyboard)

# 🌐 Вебхук
@app.route("/webhook", methods=["POST"])
def webhook():
    update = types.Update.de_json(request.get_json(force=True))
    asyncio.run(handle_update(update))
    return "OK", 200

# 🔧 Запуск локально
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
