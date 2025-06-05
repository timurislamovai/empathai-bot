from flask import Flask, request, jsonify
import os
import openai
import requests
import json

app = Flask(__name__)

# Настройки
openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")
JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID")

# URL для работы с JSONBin
JSONBIN_BASE_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"

# Функция для загрузки текста из файлов
def load_text(filename):
    filepath = os.path.join("texts", filename)
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "Текст временно недоступен."

# Загрузка данных из JSONBin
def load_user_threads():
    headers = {"X-Master-Key": JSONBIN_API_KEY}
    response = requests.get(JSONBIN_BASE_URL, headers=headers)
    if response.status_code == 200:
        return response.json().get("record", {})
    return {}

# Сохранение данных в JSONBin
def save_user_threads(data):
    headers = {
        "X-Master-Key": JSONBIN_API_KEY,
        "Content-Type": "application/json"
    }
    requests.put(JSONBIN_BASE_URL, headers=headers, json={"record": data})

# Память для хранения thread_id
user_threads = load_user_threads()

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update or "message" not in update:
        return jsonify({"status": "no message"}), 400

    message = update["message"]
    chat_id = message["chat"]["id"]
    user_message = message.get("text", "")

    # Команда /start
    if user_message == "/start":
        send_menu(chat_id)
        return jsonify({"status": "menu sent"}), 200

    # Команда /reset
    if user_message == "/reset":
        user_threads.pop(chat_id, None)
        save_user_threads(user_threads)
        send_message(chat_id, "История очищена.")
        return jsonify({"status": "reset done"}), 200

    # Обработка кнопок меню
    menu_options = {
        "Помощь": "help.txt",
        "О нас": "about.txt",
        "Сбросить диалог": None,  # Выполняется команда /reset
        "Условия": "terms.txt",
        "Вопрос ответ": "faq.txt",
    }

    if user_message in menu_options:
        if user_message == "Сбросить диалог":
            user_threads.pop(chat_id, None)
            save_user_threads(user_threads)
            send_message(chat_id, "История очищена.")
        else:
            text = load_text(menu_options[user_message])
            send_message(chat_id, text)
        return jsonify({"status": "menu option handled"}), 200

    # Работа с thread_id
    thread_id = user_threads.get(chat_id)
    if not thread_id:
        thread = openai.beta.threads.create()
        thread_id = thread.id
        user_threads[chat_id] = thread_id
        save_user_threads(user_threads)

    # Отправка сообщения в OpenAI
    openai.beta.threads.messages.create(thread_id=thread_id, role="user", content=user_message)
    run = openai.beta.threads.runs.create(thread_id=thread_id, assistant_id=ASSISTANT_ID)

    # Получение ответа ассистента
    messages = openai.beta.threads.messages.list(thread_id=thread_id)
    assistant_reply = next((msg.content[0].text.value for msg in reversed(messages.data) if msg.role == "assistant"), "")
    send_message(chat_id, assistant_reply)
    return jsonify({"status": "ok"}), 200

def send_message(chat_id, text):
    send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(send_url, json=payload)

def send_menu(chat_id):
    keyboard = {
        "keyboard": [
            [{"text": "Помощь"}],
            [{"text": "О нас"}],
            [{"text": "Сбросить диалог"}],
            [{"text": "Условия"}],
            [{"text": "Вопрос ответ"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "Выберите действие:",
        "reply_markup": keyboard
    }
    requests.post(send_url, json=payload)

if __name__ == "__main__":
    app.run(debug=True)
