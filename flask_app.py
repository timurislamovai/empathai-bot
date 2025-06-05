from flask import Flask, request, jsonify
import os
import openai
import requests
import json

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID")
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")

JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
HEADERS = {
    "X-Master-Key": JSONBIN_API_KEY,
    "Content-Type": "application/json"
}

# Загрузка истории пользователей из JSONBin
def load_user_threads():
    try:
        response = requests.get(JSONBIN_URL, headers=HEADERS)
        if response.status_code == 200:
            return response.json()["record"]
    except Exception as e:
        print("Ошибка при загрузке thread_id:", e)
    return {}

# Сохранение истории пользователей в JSONBin
def save_user_threads(threads):
    try:
        requests.put(JSONBIN_URL, headers=HEADERS, json=threads)
    except Exception as e:
        print("Ошибка при сохранении thread_id:", e)

# Загрузка текста из файла
def load_text(name):
    try:
        with open(f"texts/{name}.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "Текст временно недоступен."

# Отправка меню с кнопками
def set_menu(chat_id):
    menu_buttons = [
        [{"text": "Помощь"}, {"text": "О нас"}],
        [{"text": "Сбросить диалог"}, {"text": "Условия"}],
        [{"text": "Вопрос-ответ"}]
    ]
    payload = {
        "chat_id": chat_id,
        "reply_markup": {"keyboard": menu_buttons, "resize_keyboard": True, "one_time_keyboard": False}
    }
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json=payload)

user_threads = {}

@app.before_first_request
def initialize_threads():
    global user_threads
    user_threads = load_user_threads()

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update or "message" not in update:
        return jsonify({"status": "no message"}), 400

    message = update["message"]
    chat_id = message["chat"]["id"]
    user_message = message.get("text", "").strip()

    set_menu(chat_id)

    if user_message == "/start":
        reply_text = (
            "Привет! Меня зовут Ила — я твой виртуальный психолог и наставник по саморазвитию.\n"
            "Проект EmpathAI создан, чтобы помочь тебе обрести осознанность, разобраться в чувствах "
            "и справиться с внутренними трудностями.\n"
            "Ты можешь свободно делиться тем, что на душе — я здесь, чтобы поддержать тебя и помочь найти внутреннюю опору. 🌿"
        )
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": reply_text}
        )
        return jsonify({"status": "ok"}), 200

    if user_message.lower() == "/reset" or user_message.lower() == "сбросить диалог":
        if str(chat_id) in user_threads:
            del user_threads[str(chat_id)]
            save_user_threads(user_threads)
            reply_text = load_text("reset")
        else:
            reply_text = "История уже пуста."
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": reply_text}
        )
        return jsonify({"status": "reset"}), 200

    menu_responses = {
        "помощь": "help",
        "о нас": "about",
        "условия": "terms",
        "вопрос-ответ": "faq"
    }

    key = user_message.lower()
    if key in menu_responses:
        reply_text = load_text(menu_responses[key])
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": reply_text}
        )
        return jsonify({"status": "menu"}), 200

    thread_id = user_threads.get(str(chat_id))
    if not thread_id:
        thread = openai.beta.threads.create()
        thread_id = thread.id
        user_threads[str(chat_id)] = thread_id
        save_user_threads(user_threads)

    openai.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_message
    )

    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )

    while True:
        run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status == "completed":
            break
        elif run_status.status in ["failed", "cancelled", "expired"]:
            return jsonify({"error": "Assistant run failed"}), 500

    messages = openai.beta.threads.messages.list(thread_id=thread_id)
    assistant_reply = ""
    for msg in reversed(messages.data):
        if msg.role == "assistant":
            assistant_reply = msg.content[0].text.value
            break

    if assistant_reply:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": assistant_reply}
        )

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(debug=True)
