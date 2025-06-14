import os
import json
import requests
from flask import Flask, request
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")
JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID")

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"

HEADERS = {
    "X-Master-Key": JSONBIN_API_KEY,
    "Content-Type": "application/json"
}

client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

main_menu = {
    "keyboard": [
        [{"text": "🧠 Инструкция"}, {"text": "❓ Гид по боту"}],
        [{"text": "📜 Условия пользования"}, {"text": "💳 Купить подписку"}]
    ],
    "resize_keyboard": True
}


def get_thread_id(user_id):
    response = requests.get(JSONBIN_URL, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        threads = data["record"]
        return threads.get(str(user_id))
    return None


def save_thread_id(user_id, thread_id):
    response = requests.get(JSONBIN_URL, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        threads = data["record"]
        threads[str(user_id)] = thread_id
        requests.put(JSONBIN_URL, headers=HEADERS, json={"record": threads})


def reset_thread_id(user_id):
    response = requests.get(JSONBIN_URL, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        threads = data["record"]
        if str(user_id) in threads:
            del threads[str(user_id)]
            requests.put(JSONBIN_URL, headers=HEADERS, json={"record": threads})


def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": main_menu,
        "parse_mode": "HTML"
    }
    requests.post(url, json=data)


def read_file(file_name):
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "Файл не найден."


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data or "message" not in data:
        return "ok"

    message = data["message"]
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "")

    if text == "/start":
        welcome = read_file("support.txt")
        send_message(chat_id, welcome)
        return "ok"

    if text == "🧠 Инструкция":
        send_message(chat_id, read_file("support.txt"))
        return "ok"
    elif text == "❓ Гид по боту":
        send_message(chat_id, read_file("faq.txt"))
        return "ok"
    elif text == "📜 Условия пользования":
        send_message(chat_id, read_file("rules.txt"))
        return "ok"
    elif text == "💳 Купить подписку":
        send_message(chat_id, "Скоро будет доступно.")
        return "ok"
    elif text.lower() in ["сброс", "сбросить", "сбросить диалог"]:
        reset_thread_id(user_id)
        send_message(chat_id, read_file("reset.txt"))
        return "ok"

    thread_id = get_thread_id(user_id)

    if not thread_id:
        thread = client.beta.threads.create()
        thread_id = thread.id
        save_thread_id(user_id, thread_id)

    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=text
    )

    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )

    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        if run_status.status == "completed":
            break

    messages = client.beta.threads.messages.list(thread_id=thread_id)
    if messages.data:
        reply = messages.data[0].content[0].text.value
        send_message(chat_id, reply)

    return "ok"


@app.route("/", methods=["GET"])
def index():
    return "Telegram bot is running."


if __name__ == "__main__":
    app.run(debug=True)
