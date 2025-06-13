# 🔧 Полный рабочий flask_app.py с пробным периодом

import os
import logging
import requests
from flask import Flask, request, jsonify
from datetime import datetime
from dotenv import load_dotenv
from functools import wraps

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ASSISTANT_ID = os.getenv("ASSISTANT_ID")
    JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")
    JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{os.getenv('JSONBIN_BIN_ID')}"
    MAX_RETRIES = 3
    REQUEST_TIMEOUT = 7

# Инициализация Flask
app = Flask(__name__)

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Утилиты
def retry(max_attempts=3):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
        return wrapper
    return decorator

def handle_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return None
    return wrapper

# Работа с Telegram
class TelegramAPI:
    URL = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"

    @staticmethod
    def send_message(chat_id, text, reply_markup=None):
        messages = TelegramAPI.split_text(text)
        for msg in messages:
            payload = {
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": "HTML"
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup
            requests.post(TelegramAPI.URL, json=payload)

    @staticmethod
    def split_text(text):
        max_len = 4096
        return [text[i:i+max_len] for i in range(0, len(text), max_len)]

    @staticmethod
    def main_menu():
        return {
            "keyboard": [["Помощь", "О нас"], ["Сбросить диалог", "Условия", "Вопрос-ответ"]],
            "resize_keyboard": True
        }

# Работа с текстами
class FileManager:
    @staticmethod
    def get_text_content(filename):
        path = os.path.join("texts", filename)
        with open(path, "r", encoding="utf-8") as file:
            return file.read()

# Работа с OpenAI
class OpenAIAssistant:
    @staticmethod
    def create_thread():
        url = "https://api.openai.com/v1/threads"
        headers = {"Authorization": f"Bearer {Config.OPENAI_API_KEY}"}
        response = requests.post(url, headers=headers, timeout=Config.REQUEST_TIMEOUT)
        return response.json().get("id")

    @staticmethod
    def send_message(thread_id, message):
        url = f"https://api.openai.com/v1/threads/{thread_id}/messages"
        headers = {
            "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {"role": "user", "content": message}
        requests.post(url, headers=headers, json=data, timeout=Config.REQUEST_TIMEOUT)

    @staticmethod
    def get_response(thread_id):
        run_url = f"https://api.openai.com/v1/threads/{thread_id}/runs"
        headers = {
            "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        run = requests.post(run_url, headers=headers, json={"assistant_id": Config.ASSISTANT_ID}, timeout=Config.REQUEST_TIMEOUT)
        run_id = run.json().get("id")

        # Проверка готовности ответа
        import time
        for _ in range(10):
            time.sleep(0.8)
            status = requests.get(status_url, headers=headers, timeout=Config.REQUEST_TIMEOUT).json()
            if status.get("status") in ["completed", "failed"]:
                break

        msg_url = f"https://api.openai.com/v1/threads/{thread_id}/messages"
        messages = requests.get(msg_url, headers=headers, timeout=Config.REQUEST_TIMEOUT).json()
        if not messages.get("data"):
    return "Извините, я не смог получить ответ. Попробуй ещё раз."

    content = messages["data"][0]["content"][0]["text"]["value"]
    return content
        content = messages["data"][0]["content"][0]["text"]["value"]
        return content

# Работа с JSONBin
class DataStorage:
    @staticmethod
    @handle_errors
    @retry()
    def get_thread_id(chat_id):
        headers = {"X-Master-Key": Config.JSONBIN_API_KEY}
        response = requests.get(Config.JSONBIN_URL, headers=headers, timeout=Config.REQUEST_TIMEOUT)
        if response.status_code == 200:
            data = response.json().get("record", {})
            return data.get(str(chat_id), {}).get("thread_id")
        return None

    @staticmethod
    @handle_errors
    @retry()
    def save_thread_id(chat_id, thread_id):
        headers = {
            "X-Master-Key": Config.JSONBIN_API_KEY,
            "Content-Type": "application/json"
        }
        response = requests.get(Config.JSONBIN_URL, headers=headers, timeout=Config.REQUEST_TIMEOUT)
        record = response.json().get("record", {}) if response.status_code == 200 else {}
        user_data = record.get(str(chat_id), {})
        user_data["thread_id"] = thread_id
        record[str(chat_id)] = user_data
        requests.put(Config.JSONBIN_URL, headers=headers, json=record, timeout=Config.REQUEST_TIMEOUT)

    @staticmethod
    @handle_errors
    @retry()
    def reset_thread_id(chat_id):
        headers = {
            "X-Master-Key": Config.JSONBIN_API_KEY,
            "Content-Type": "application/json"
        }
        response = requests.get(Config.JSONBIN_URL, headers=headers, timeout=Config.REQUEST_TIMEOUT)
        record = response.json().get("record", {}) if response.status_code == 200 else {}
        if str(chat_id) in record:
            record[str(chat_id)]["thread_id"] = None
        requests.put(Config.JSONBIN_URL, headers=headers, json=record, timeout=Config.REQUEST_TIMEOUT)

# 🔐 Логика пробного периода
class TrialManager:
    MAX_DAYS = 3
    DAILY_LIMIT = 15

    @staticmethod
    def get_today():
        return datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    @handle_errors
    @retry()
    def get_user_data(chat_id):
        headers = {"X-Master-Key": Config.JSONBIN_API_KEY}
        response = requests.get(Config.JSONBIN_URL, headers=headers, timeout=Config.REQUEST_TIMEOUT)
        if response.status_code == 200:
            data = response.json().get("record", {})
            return data.get(str(chat_id), {})
        return {}

    @staticmethod
    @handle_errors
    @retry()
    def update_user_data(chat_id, new_data):
        headers = {
            "X-Master-Key": Config.JSONBIN_API_KEY,
            "Content-Type": "application/json"
        }
        response = requests.get(Config.JSONBIN_URL, headers=headers, timeout=Config.REQUEST_TIMEOUT)
        record = response.json().get("record", {}) if response.status_code == 200 else {}
        record[str(chat_id)] = {**record.get(str(chat_id), {}), **new_data}
        requests.put(Config.JSONBIN_URL, headers=headers, json=record, timeout=Config.REQUEST_TIMEOUT)

    @staticmethod
    def is_trial_expired(user_data):
        start = user_data.get("trial_start")
        if not start:
            return False
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d")
            return (datetime.now() - start_date).days >= TrialManager.MAX_DAYS
        except Exception:
            return False

    @staticmethod
    def is_limit_exceeded(user_data):
        last_active = user_data.get("last_active")
        today = TrialManager.get_today()
        if last_active != today:
            return False
        return int(user_data.get("daily_count", 0)) >= TrialManager.DAILY_LIMIT

    @staticmethod
    def process_usage(chat_id):
        today = TrialManager.get_today()
        user_data = TrialManager.get_user_data(chat_id)
        if not user_data:
            TrialManager.update_user_data(chat_id, {
                "trial_start": today,
                "daily_count": 1,
                "last_active": today
            })
            return True, "🎉 Привет! Тебе доступен 3-дневный пробный период (15 сообщений в день)."
        if TrialManager.is_trial_expired(user_data):
            return False, "⛔ Пробный период завершён. Оформи подписку, чтобы продолжить."
        if TrialManager.is_limit_exceeded(user_data):
            return False, "⛔ Достигнут лимит 15 сообщений на сегодня. Попробуй завтра или оформи подписку."
        count = 1 if user_data.get("last_active") != today else int(user_data.get("daily_count", 0)) + 1
        TrialManager.update_user_data(chat_id, {
            "daily_count": count,
            "last_active": today
        })
        return True, None

# 🔁 Webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if "message" not in data:
        return jsonify({"ok": True})

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")

    allowed, message = TrialManager.process_usage(chat_id)
    if not allowed:
        TelegramAPI.send_message(chat_id, message, TelegramAPI.main_menu())
        return jsonify({"ok": True})

    if text.lower() == "помощь":
        TelegramAPI.send_message(chat_id, FileManager.get_text_content("support.txt"), TelegramAPI.main_menu())
    elif text.lower() == "о нас":
        TelegramAPI.send_message(chat_id, FileManager.get_text_content("info.txt"), TelegramAPI.main_menu())
    elif text.lower() == "условия":
        TelegramAPI.send_message(chat_id, FileManager.get_text_content("rules.txt"), TelegramAPI.main_menu())
    elif text.lower() == "вопрос-ответ":
        TelegramAPI.send_message(chat_id, FileManager.get_text_content("faq.txt"), TelegramAPI.main_menu())
    elif text.lower() == "сбросить диалог":
        DataStorage.reset_thread_id(chat_id)
        TelegramAPI.send_message(chat_id, FileManager.get_text_content("reset.txt"), TelegramAPI.main_menu())
    else:
        thread_id = DataStorage.get_thread_id(chat_id)
        if not thread_id:
            thread_id = OpenAIAssistant.create_thread()
            DataStorage.save_thread_id(chat_id, thread_id)

        OpenAIAssistant.send_message(thread_id, text)
        answer = OpenAIAssistant.get_response(thread_id)
        TelegramAPI.send_message(chat_id, answer, TelegramAPI.main_menu())

    return jsonify({"ok": True})


   if __name__ == "__main__":
       port = int(os.environ.get("PORT", 5000))
       app.run(host="0.0.0.0", port=port)
