from flask import Flask, request, jsonify
import os
import openai
import requests
import json

app = Flask(__name__)

# Настройки OpenAI и Telegram
openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

# Настройки JSONBin.io для хранения thread_id
JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID")  # например: "6841468c8960c979a5a57459"
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")  # ключ с правами записи

JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"

HEADERS = {
    "X-Master-Key": JSONBIN_API_KEY,
    "Content-Type": "application/json"
}

# Кнопки меню
MENU_BUTTONS = [
    ["Помощь", "О нас"],
    ["Сбросить диалог", "Условия"],
    ["Вопрос-ответ"]
]

def get_user_threads():
    """Загружаем данные с JSONBin (chat_id -> thread_id)"""
    try:
        r = requests.get(JSONBIN_URL + "/latest", headers=HEADERS)
        if r.status_code == 200:
            return r.json()["record"]
    except Exception as e:
        print("Ошибка при загрузке thread_id из JSONBin:", e)
    return {}

def save_user_threads(data):
    """Сохраняем данные в JSONBin"""
    try:
        r = requests.put(JSONBIN_URL, headers=HEADERS, json=data)
        return r.status_code == 200 or r.status_code == 201
    except Exception as e:
        print("Ошибка при сохранении thread_id в JSONBin:", e)
        return False

user_threads = get_user_threads()

def send_menu(chat_id):
    keyboard = {
        "keyboard": MENU_BUTTONS,
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "Выберите опцию из меню:",
        "reply_markup": keyboard
    }
    requests.post(send_url, json=payload)

def send_message(chat_id, text):
    send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    keyboard = {
        "keyboard": MENU_BUTTONS,
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": keyboard
    }
    requests.post(send_url, json=payload)

def load_text(filename):
    try:
        with open(f"texts/{filename}", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Текст не найден."

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update:
        return jsonify({"status": "no update"}), 400

    message = update.get("message")
    if not message:
        return jsonify({"status": "no message"}), 200

    chat_id = message["chat"]["id"]
    user_text = message.get("text", "").strip()

    if not user_text:
        send_menu(chat_id)
        return jsonify({"status": "no text"}), 200

    # Обработка пунктов меню (тексты из файлов)
    if user_text == "Помощь":
        text = load_text("help.txt")
        send_message(chat_id, text)
        return jsonify({"status": "help sent"}), 200
    elif user_text == "О нас":
        text = load_text("about.txt")
        send_message(chat_id, text)
        return jsonify({"status": "about sent"}), 200
    elif user_text == "Условия":
        text = load_text("terms.txt")
        send_message(chat_id, text)
        return jsonify({"status": "terms sent"}), 200
    elif user_text == "Вопрос-ответ":
        text = load_text("faq.txt")
        send_message(chat_id, text)
        return jsonify({"status": "faq sent"}), 200
    elif user_text == "Сбросить диалог":
        # Сброс истории пользователя
        if str(chat_id) in user_threads:
            user_threads.pop(str(chat_id))
            save_user_threads(user_threads)
        reset_msg = load_text("reset.txt")
        send_message(chat_id, reset_msg)
        return jsonify({"status": "reset done"}), 200
    elif user_text == "/reset":
        # То же действие для команды /reset
        if str(chat_id) in user_threads:
            user_threads.pop(str(chat_id))
            save_user_threads(user_threads)
        reset_msg = load_text("reset.txt")
        send_message(chat_id, reset_msg)
        return jsonify({"status": "reset done"}), 200

    # Работа с OpenAI Assistant и thread_id
    thread_id = user_threads.get(str(chat_id))
    if not thread_id:
        # Создаём новый thread
        try:
            thread = openai.beta.threads.create()
            thread_id = thread.id
            user_threads[str(chat_id)] = thread_id
            save_user_threads(user_threads)
        except Exception as e:
            print("Ошибка при создании треда:", e)
            send_message(chat_id, "Ошибка сервера, попробуйте позже.")
            return jsonify({"status": "error"}), 500

    try:
        # Отправляем сообщение пользователя в тред
        openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_text
        )
        # Запускаем ассистента
        run = openai.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        # Ожидаем завершения run
        while True:
            run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if run_status.status == "completed":
                break
            elif run_status.status in ["failed", "cancelled", "expired"]:
                send_message(chat_id, "Ошибка при обработке запроса. Попробуйте позже.")
                return jsonify({"status": "run failed"}), 500

        # Получаем ответ ассистента
        messages = openai.beta.threads.messages.list(thread_id=thread_id)
        assistant_reply = ""
        for msg in reversed(messages.data):
            if msg.role == "assistant":
                assistant_reply = msg.content[0].text.value
                break

        if assistant_reply:
            send_message(chat_id, assistant_reply)
        else:
            send_message(chat_id, "Извините, я не смог ответить на ваш вопрос.")

    except Exception as e:
        print("Ошибка при общении с OpenAI:", e)
        send_message(chat_id, "Ошибка сервера, попробуйте позже.")
        return jsonify({"status": "error"}), 500

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(debug=True)
