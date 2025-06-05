from flask import Flask, request, jsonify
import os
import openai
import requests
import json

app = Flask(__name__)

# Настройки OpenAI и Telegram из переменных окружения
openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

# Настройки jsonbin.io
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")  # сюда вставь свой X-Master-Key
BIN_ID = "6841468c8960c979a5a57459"            # твой bin_id

# Кэш для хранения thread_id, загружается из jsonbin при старте
user_threads = {}

def load_threads_from_jsonbin():
    global user_threads
    url = f"https://api.jsonbin.io/v3/b/{BIN_ID}/latest"
    headers = {
        "X-Master-Key": JSONBIN_API_KEY,
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            # Ожидается, что данные — это словарь chat_id -> thread_id
            user_threads = data.get("record", {})
            print("user_threads загружены из jsonbin")
        else:
            print(f"Ошибка загрузки jsonbin: {response.status_code} {response.text}")
    except Exception as e:
        print("Исключение при загрузке jsonbin:", e)

def save_threads_to_jsonbin():
    url = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
    headers = {
        "X-Master-Key": JSONBIN_API_KEY,
        "Content-Type": "application/json"
    }
    payload = json.dumps(user_threads)
    try:
        response = requests.put(url, headers=headers, data=payload)
        if response.status_code == 200:
            print("user_threads сохранены в jsonbin")
        else:
            print(f"Ошибка сохранения jsonbin: {response.status_code} {response.text}")
    except Exception as e:
        print("Исключение при сохранении jsonbin:", e)

@app.before_first_request
def startup():
    # При запуске загружаем thread_id из jsonbin
    load_threads_from_jsonbin()

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update or "message" not in update:
        return jsonify({"status": "no message"}), 400

    message = update["message"]
    chat_id = str(message["chat"]["id"])
    user_message = message.get("text", "")

    if not user_message:
        return jsonify({"status": "no text"}), 200

    # Получаем или создаём thread для пользователя
    thread_id = user_threads.get(chat_id)
    if not thread_id:
        thread = openai.beta.threads.create()
        thread_id = thread.id
        user_threads[chat_id] = thread_id
        save_threads_to_jsonbin()

    # Отправка сообщения в тред
    openai.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_message
    )

    # Запуск ассистента
    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )

    # Ожидание завершения run
    while True:
        run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status == "completed":
            break
        elif run_status.status in ["failed", "cancelled", "expired"]:
            return jsonify({"error": "Assistant run failed"}), 500

    # Получение ответа ассистента
    messages = openai.beta.threads.messages.list(thread_id=thread_id)
    assistant_reply = ""
    for msg in reversed(messages.data):
        if msg.role == "assistant":
            assistant_reply = msg.content[0].text.value
            break

    # Отправка ответа в Telegram
    if assistant_reply:
        send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": assistant_reply}
        try:
            requests.post(send_url, json=payload)
        except Exception as e:
            print("Ошибка при отправке сообщения в Telegram:", e)

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(debug=True)
