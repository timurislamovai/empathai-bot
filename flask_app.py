import os
import time
import json
import requests
import openai
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

openai.api_key = OPENAI_API_KEY


def main_menu():
    return {
        "keyboard": [
            [{"text": "🧠 Инструкция"}, {"text": "❓ Гид по боту"}],
            [{"text": "🔄 Сбросить диалог"}, {"text": "💳 Купить подписку"}],
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


def create_thread():
    response = openai.beta.threads.create()
    return response.id


def send_to_assistant(chat_id, user_input):
    thread_id = get_thread_id(chat_id)
    if not thread_id:
        thread_id = create_thread()
        save_thread_id(chat_id, thread_id)

    openai.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_input
    )

    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )

    while True:
        run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status == "completed":
            break
        elif run_status.status == "failed":
            return "❌ Ошибка выполнения запроса."
        time.sleep(1)

    messages = openai.beta.threads.messages.list(thread_id=thread_id)
    for msg in reversed(messages.data):
        if msg.role == "assistant":
            return msg.content[0].text.value

    return "🤖 Нет ответа от ассистента."


def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"[ERROR] Telegram send failed: {response.status_code} {response.text}")


def send_predefined_response(chat_id, command):
    file_map = {
        "🧠 Инструкция": "support.txt",
        "❓ Гид по боту": "faq.txt",
        "📜 Условия пользования": "rules.txt",
        "💳 Купить подписку": "pay.txt"
    }
    filename = file_map.get(command)
    if filename and os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
        send_message(chat_id, content, reply_markup=main_menu())


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

    if text == "🔄 Сбросить диалог":
        reset_thread_id(chat_id)
        send_message(chat_id, "Диалог успешно сброшен.", reply_markup=main_menu())
        return

    elif text in […command for command in [“🧠 Инструкция”, “❓ Гид по боту”, “📜 Условия пользования”, “💳 Купить подписку”]]:
        send_predefined_response(chat_id, text)
        return

    assistant_reply = send_to_assistant(chat_id, text)
    send_message(chat_id, assistant_reply, reply_markup=main_menu())
