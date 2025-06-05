from flask import Flask, request, jsonify
import os
import openai
import requests

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

# Память для хранения thread_id по chat_id
user_threads = {}

# Функция для чтения текста из файлов
def get_text_from_file(filename):
    try:
        with open(os.path.join("texts", filename), "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "Извините, информация временно недоступна."

# Функция отправки сообщений в Telegram
def send_message(chat_id, text):
    send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(send_url, json=payload)
    except Exception as e:
        print("Ошибка при отправке сообщения в Telegram:", e)

# Обработка входящих сообщений
@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update or "message" not in update:
        return jsonify({"status": "no message"}), 400

    message = update["message"]
    chat_id = message["chat"]["id"]
    user_message = message.get("text", "").strip()

    if not user_message:
        return jsonify({"status": "no text"}), 200

    # Обработка меню
    if user_message == "Помощь":
        text = get_text_from_file("help.txt")
        send_message(chat_id, text)
        return jsonify({"status": "ok"}), 200

    elif user_message == "О нас":
        text = get_text_from_file("about.txt")
        send_message(chat_id, text)
        return jsonify({"status": "ok"}), 200

    elif user_message == "Сбросить диалог":
        # Очистка истории пользователя
        if chat_id in user_threads:
            del user_threads[chat_id]
        text = get_text_from_file("reset.txt")
        send_message(chat_id, text)
        return jsonify({"status": "ok"}), 200

    elif user_message == "Условия":
        text = get_text_from_file("terms.txt")
        send_message(chat_id, text)
        return jsonify({"status": "ok"}), 200

    elif user_message == "Вопрос ответ":
        text = get_text_from_file("faq.txt")
        send_message(chat_id, text)
        return jsonify({"status": "ok"}), 200

    # Обработка обычных сообщений через OpenAI Assistant
    thread_id = user_threads.get(chat_id)
    if not thread_id:
        thread = openai.beta.threads.create()
        thread_id = thread.id
        user_threads[chat_id] = thread_id

    openai.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_message
    )

    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )

    # Ожидание завершения run (упрощённо)
    while True:
        run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status == "completed":
            break
        elif run_status.status in ["failed", "cancelled", "expired"]:
            send_message(chat_id, "Произошла ошибка при обработке вашего запроса.")
            return jsonify({"error": "Assistant run failed"}), 500

    messages = openai.beta.threads.messages.list(thread_id=thread_id)
    assistant_reply = ""
    for msg in reversed(messages.data):
        if msg.role == "assistant":
            assistant_reply = msg.content[0].text.value
            break

    if assistant_reply:
        send_message(chat_id, assistant_reply)

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(debug=True)
