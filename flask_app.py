from flask import Flask, request, jsonify
import os
import openai
import requests

app = Flask(__name__)

# Настройки OpenAI и Telegram
openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

# Память для хранения thread_id по chat_id
user_threads = {}

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update or "message" not in update:
        return jsonify({"status": "no message"}), 400

    message = update["message"]
    chat_id = message["chat"]["id"]
    user_message = message.get("text", "")

    if not user_message:
        return jsonify({"status": "no text"}), 200

    # Получаем или создаём thread для пользователя
    thread_id = user_threads.get(chat_id)
    if not thread_id:
        thread = openai.beta.threads.create()
        thread_id = thread.id
        user_threads[chat_id] = thread_id

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
