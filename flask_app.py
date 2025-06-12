import os
import time
import json
import requests
from flask import Flask, request
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")
JSONBIN_THREAD_BIN = os.getenv("JSONBIN_BIN_ID")
JSONBIN_USER_BIN = os.getenv("JSONBIN_USER_BIN_ID")

THREAD_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_THREAD_BIN}"
USER_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_USER_BIN}"

SYSTEM_BUTTONS = ["🧠 Инструкция", "❓ Гид по боту", "💳 Купить подписку", "📜 Условия пользования", "🔄 Сбросить диалог"]


def main_menu():
    return {
        "keyboard": [
            [{"text": "🧠 Инструкция"}, {"text": "❓ Гид по боту"}],
            [{"text": "🔄 Сбросить диалог"}, {"text": "💳 Купить подписку"}],
            [{"text": "📜 Условия пользования"}]
        ],
        "resize_keyboard": True
    }

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(url, json=payload)

# ========== Thread ID Management ==========

def get_jsonbin_data(url):
    headers = {"X-Master-Key": JSONBIN_API_KEY}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return res.json().get("record", {})
    except: pass
    return {}

def update_jsonbin_data(url, data):
    headers = {
        "X-Master-Key": JSONBIN_API_KEY,
        "Content-Type": "application/json"
    }
    try:
        requests.put(url, headers=headers, json=data)
    except: pass

def get_thread_id(chat_id):
    data = get_jsonbin_data(THREAD_URL)
    return data.get(str(chat_id))

def save_thread_id(chat_id, thread_id):
    data = get_jsonbin_data(THREAD_URL)
    data[str(chat_id)] = thread_id
    update_jsonbin_data(THREAD_URL, data)

def reset_thread_id(chat_id):
    data = get_jsonbin_data(THREAD_URL)
    if str(chat_id) in data:
        del data[str(chat_id)]
        update_jsonbin_data(THREAD_URL, data)

# ========== User Limit Management ==========

def get_user_data(chat_id):
    data = get_jsonbin_data(USER_URL)
    return data.get(str(chat_id), {})

def save_user_data(chat_id, user_data):
    data = get_jsonbin_data(USER_URL)
    data[str(chat_id)] = user_data
    update_jsonbin_data(USER_URL, data)

def check_limit(chat_id):
    user = get_user_data(chat_id)
    today = datetime.now().strftime("%Y-%m-%d")

    if not user:
        user = {"daily_count": 0, "last_date": today, "trial_active": True, "trial_start": today}

    if not user.get("trial_active", False):
        return False

    if user.get("last_date") != today:
        user["daily_count"] = 0
        user["last_date"] = today

    if user["daily_count"] >= 15:
        return False

    user["daily_count"] += 1
    save_user_data(chat_id, user)
    return True

# ========== Flask Route & Main Logic ==========
@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    handle_update(update)
    return "OK"

def handle_update(update):
    message = update.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()

    if not chat_id or not text:
        return

    if text == "/start":
        send_message(chat_id, (
            "👋 Добро пожаловать в EmpathAI!\n\n"
            "Я твой виртуальный помощник для поддержки, саморазвития и снижения тревожности.\n\n"
            "📋 Выбери пункт из меню, чтобы начать общение."
        ), reply_markup=main_menu())
        return

    if text == "🔄 Сбросить диалог":
        reset_thread_id(chat_id)
        send_message(chat_id, "Диалог сброшен. Начнем заново?", reply_markup=main_menu())
        return

    if text in SYSTEM_BUTTONS:
        filename = {
            "🧠 Инструкция": "support",
            "❓ Гид по боту": "faq",
            "💳 Купить подписку": "subscribe",
            "📜 Условия пользования": "rules"
        }.get(text)
        try:
            with open(f"texts/{filename}.txt", "r", encoding="utf-8") as f:
                send_message(chat_id, f.read(), reply_markup=main_menu())
        except:
            send_message(chat_id, "Файл не найден.", reply_markup=main_menu())
        return

    # GPT-запрос — здесь проверка лимита!
    if not check_limit(chat_id):
        send_message(chat_id, "💡 Вы использовали лимит сообщений на сегодня. Активируйте подписку, чтобы продолжить.", reply_markup=main_menu())
        return

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "assistants=v2",
        "Content-Type": "application/json"
    }

    thread_id = get_thread_id(chat_id)
    if not thread_id:
        res = requests.post("https://api.openai.com/v1/threads", headers=headers)
        if res.status_code != 200:
            send_message(chat_id, "❌ Ошибка инициализации сессии GPT.", reply_markup=main_menu())
            return
        thread_id = res.json()["id"]
        save_thread_id(chat_id, thread_id)

    requests.post(
        f"https://api.openai.com/v1/threads/{thread_id}/messages",
        headers=headers,
        json={"role": "user", "content": text}
    )

    run_res = requests.post(
        f"https://api.openai.com/v1/threads/{thread_id}/runs",
        headers=headers,
        json={"assistant_id": ASSISTANT_ID}
    )

    if run_res.status_code != 200:
        send_message(chat_id, "❌ Ошибка запуска GPT-сессии.", reply_markup=main_menu())
        return

    run_id = run_res.json()["id"]

    for _ in range(30):
        time.sleep(1)
        run_status = requests.get(
            f"https://api.openai.com/v1/threads/{thread_id}/runs/{run_id}",
            headers=headers
        ).json()
        if run_status.get("status") == "completed":
            break
    else:
        send_message(chat_id, "⏳ Время ожидания ответа GPT истекло.", reply_markup=main_menu())
        return

    messages_res = requests.get(
        f"https://api.openai.com/v1/threads/{thread_id}/messages",
        headers=headers
    )

    if messages_res.status_code != 200:
        send_message(chat_id, "❌ Ошибка получения ответа от GPT.", reply_markup=main_menu())
        return

    for msg in reversed(messages_res.json().get("data", [])):
        if msg["role"] == "assistant":
            response_text = msg["content"][0]["text"]["value"]
            send_message(chat_id, response_text, reply_markup=main_menu())
            return

    send_message(chat_id, "🤖 Ответ от GPT не получен.", reply_markup=main_menu())
