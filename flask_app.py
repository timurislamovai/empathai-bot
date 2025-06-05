from flask import Flask, request, jsonify
import os
import openai
import requests
import json

app = Flask(__name__)

# API ключи
openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

# jsonbin.io
JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID")
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")
JSONBIN_BASE_URL = os.getenv("JSONBIN_BASE_URL", "https://api.jsonbin.io/v3")

# Заголовки для jsonbin
headers = {
    "Content-Type": "application/json",
    "X-Master-Key": JSONBIN_API_KEY
}

def load_threads():
    url = f"{JSONBIN_BASE_URL}/b/{JSONBIN_BIN_ID}/latest"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("record", {})
    else:
        return {}

def save_threads(threads):
    url = f"{JSONBIN_BASE_URL}/b/{JSONBIN_BIN_ID}"
    response = requests.put(url, headers=headers, json=threads)
    return response.status_code == 200

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

    # Загрузка сохранённых thread_id
    user_threads = load_threads()

    # Обработка команды /reset
    if user_message.strip() == "/reset":
        if chat_id in user_threads:
            del user_threads[chat_id]
            save_threads(user_threads)
            send_message(chat_id, "История очищена. Начнём сначала.")
        else:
            send_message(chat_id, "История уже пуста.")
        return jsonify({"status": "reset done"}), 200

    # Получаем или создаём новый thread_id
    thread_id = user_threads.get(chat_id)
    if not thread_id:
        thread = openai.beta.threads.create()
        thread_id = thread.id
        user_threads[chat_id] = thread_id
        save_threads(user_threads)

    print(f"[DEBUG] chat_id: {chat_id}, thread_id: {thread_id}")

    # Отправляем сообщение в OpenAI thread
    openai.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_message
    )

    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )

    # Ждём завершения выполнения
    while True:
        run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status == "completed":
            break
        elif run_status.status in ["failed", "cancelled", "expired"]:
            return jsonify({"error": "Assistant run failed"}), 500

    # Получаем ответ
    messages = openai.beta.threads.messages.list(thread_id=thread_id)
    assistant_reply = ""
    for msg in reversed(messages.data):
        if msg.role == "assistant":
            assistant_reply = msg.content[0].text.value
            break

    if assistant_reply:
        send_message(chat_id, assistant_reply)

    return jsonify({"status": "ok"}), 200

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"[ERROR] Failed to send message: {e}")

if __name__ == "__main__":
    app.run(debug=True)
