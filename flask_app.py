import os
import time
import json
import requests
from flask import Flask, request
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")
JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID")
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"

def main_menu():
    return {
        "keyboard": [
            [{"text": "🧠 Инструкция"}, {"text": "❓ Гид по боту"}],
            [{"text": "ℹ️ О Сервисе"}, {"text": "🔄 Сбросить диалог"}],
            [{"text": "📜 Условия пользования"}]
        ],
        "resize_keyboard": True
    }

def get_thread_id(chat_id):
    headers = {"X-Master-Key": JSONBIN_API_KEY}
    try:
        res = requests.get(JSONBIN_URL, headers=headers)
        if res.status_code == 200:
            data = res.json().get("record", {})
            return data.get(str(chat_id))
    except Exception as e:
        print(f"[ERROR] get_thread_id: {e}")
    return None

def save_thread_id(chat_id, thread_id):
    headers = {
        "X-Master-Key": JSONBIN_API_KEY,
        "Content-Type": "application/json"
    }
    try:
        res = requests.get(JSONBIN_URL, headers=headers)
        data = res.json().get("record", {}) if res.status_code == 200 else {}
        data[str(chat_id)] = thread_id
        requests.put(JSONBIN_URL, headers=headers, json=data)
    except Exception as e:
        print(f"[ERROR] save_thread_id: {e}")

def reset_thread_id(chat_id):
    headers = {
        "X-Master-Key": JSONBIN_API_KEY,
        "Content-Type": "application/json"
    }
    try:
        res = requests.get(JSONBIN_URL, headers=headers)
        if res.status_code == 200:
            data = res.json().get("record", {})
            if str(chat_id) in data:
                del data[str(chat_id)]
                requests.put(JSONBIN_URL, headers=headers, json=data)
    except Exception as e:
        print(f"[ERROR] reset_thread_id: {e}")

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"[ERROR] Telegram send failed: {response.status_code} {response.text}")

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = request.get_json()
        handle_update(update)
        return "OK"
    except Exception as e:
        print(f"[ERROR] Webhook exception: {e}")
        return "Internal Server Error", 500

def handle_update(update):
    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    if text == "/start":
        welcome_text = (
            "👋 Добро пожаловать в EmpathAI!\n\n"
            "Я твой виртуальный помощник для поддержки, саморазвития и снижения тревожности.\n\n"
            "📋 Выбери пункт из меню, чтобы начать общение."
        )
        send_message(chat_id, welcome_text, reply_markup=main_menu())
        return

    if text == "🔄 Сбросить диалог":
        reset_thread_id(chat_id)
        send_message(chat_id, "Диалог сброшен. Начнем заново?", reply_markup=main_menu())
        return

    if text in ["🧠 Инструкция", "❓ Гид по боту", "ℹ️ О Сервисе", "📜 Условия пользования"]:
        filename = {
            "🧠 Инструкция": "support",
            "❓ Гид по боту": "faq",
            "ℹ️ О Сервисе": "info",
            "📜 Условия пользования": "rules"
        }.get(text, "faq")
        try:
            with open(f"texts/{filename}.txt", "r", encoding="utf-8") as f:
                content = f.read()
        except:
            content = "Файл не найден."
        send_message(chat_id, content, reply_markup=main_menu())
        return

    # GPT-переписка
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "assistants=v2",
        "Content-Type": "application/json"
    }

    thread_id = get_thread_id(chat_id)
    if not thread_id:
        thread_res = requests.post("https://api.openai.com/v1/threads", headers=headers)
        if thread_res.status_code != 200:
            send_message(chat_id, "❌ Ошибка инициализации сессии.", reply_markup=main_menu())
            return
        thread_id = thread_res.json()["id"]
        save_thread_id(chat_id, thread_id)

    msg_payload = {"role": "user", "content": text}
    requests.post(
        f"https://api.openai.com/v1/threads/{thread_id}/messages",
        headers=headers,
        json=msg_payload
    )

    run_payload = {"assistant_id": ASSISTANT_ID}
    run_res = requests.post(
        f"https://api.openai.com/v1/threads/{thread_id}/runs",
        headers=headers,
        json=run_payload
    )

    if run_res.status_code != 200:
        send_message(chat_id, "❌ Ошибка запуска AI-сессии.", reply_markup=main_menu())
        return

    run_id = run_res.json()["id"]

    for _ in range(30):
        time.sleep(1)
        check = requests.get(
            f"https://api.openai.com/v1/threads/{thread_id}/runs/{run_id}",
            headers=headers
        )
        status = check.json().get("status")
        if status == "completed":
            break
    else:
        send_message(chat_id, "⏳ Превышено время ожидания ответа.", reply_markup=main_menu())
        return

    messages_res = requests.get(
        f"https://api.openai.com/v1/threads/{thread_id}/messages",
        headers=headers
    )

    if messages_res.status_code != 200:
        send_message(chat_id, "❌ Ошибка получения ответа.", reply_markup=main_menu())
        return

    messages = messages_res.json().get("data", [])
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            response_text = msg["content"][0]["text"]["value"]
            send_message(chat_id, response_text, reply_markup=main_menu())
            return

    send_message(chat_id, "🤖 Ответ не найден.", reply_markup=main_menu())
