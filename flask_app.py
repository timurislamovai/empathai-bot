import os
import time
import json
import requests
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from functools import wraps
from threading import Thread
import signal
import sys

# Настройка логирования для Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]  # Только stdout для Render
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)

# Конфигурация
class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ASSISTANT_ID = os.getenv("ASSISTANT_ID")
    JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")
    JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID")
    JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
    
    # Тайм-ауты и лимиты (адаптированы для Render)
    REQUEST_TIMEOUT = 15  # Увеличен для медленных соединений
    MAX_RETRIES = 2       # Уменьшен для экономии ресурсов
    OPENAI_WAIT_TIMEOUT = 25  # Оптимизирован для бесплатного тарифа
    TELEGRAM_MESSAGE_LIMIT = 4096

# Валидация конфигурации
def validate_config():
    required_vars = [
        'TELEGRAM_BOT_TOKEN', 'OPENAI_API_KEY', 'ASSISTANT_ID',
        'JSONBIN_API_KEY', 'JSONBIN_BIN_ID'
    ]
    missing = [var for var in required_vars if not getattr(Config, var)]
    if missing:
        logger.error(f"Отсутствуют обязательные переменные окружения: {missing}")
        return False
    return True

# Декоратор для обработки ошибок
def handle_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка в {func.__name__}: {e}")
            return None
    return wrapper

# Декоратор для retry логики (упрощен для экономии ресурсов)
def retry(max_attempts=2, delay=0.5):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        logger.error(f"Все попытки исчерпаны для {func.__name__}: {e}")
                        raise
                    logger.warning(f"Повтор {attempt + 1} для {func.__name__}: {e}")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

class TelegramAPI:
    @staticmethod
    def main_menu():
        return {
            "keyboard": [
                [{"text": "🧠 Инструкция"}, {"text": "❓ Гид по боту"}],
                [{"text": "🔄 Сбросить диалог"}, {"text": "💳 Купить подписку"}],
                [{"text": "📜 Условия пользования"}, {"text": "ℹ️ Информация"}],
                [{"text": "🆓 Пробный период"}]
            ],
            "resize_keyboard": True
        }

    @staticmethod
    @retry(max_attempts=Config.MAX_RETRIES)
    def send_message(chat_id, text, reply_markup=None):
        """Отправка сообщения с обработкой лимитов длины"""
        if not text:
            logger.warning("Попытка отправить пустое сообщение")
            return False
            
        # Разбиваем длинные сообщения
        if len(text) > Config.TELEGRAM_MESSAGE_LIMIT:
            parts = [text[i:i+Config.TELEGRAM_MESSAGE_LIMIT] 
                    for i in range(0, len(text), Config.TELEGRAM_MESSAGE_LIMIT)]
            for i, part in enumerate(parts):
                markup = reply_markup if i == len(parts) - 1 else None
                if not TelegramAPI._send_single_message(chat_id, part, markup):
                    return False
                time.sleep(0.1)  # Небольшая задержка между сообщениями
            return True
        else:
            return TelegramAPI._send_single_message(chat_id, text, reply_markup)

    @staticmethod
    def _send_single_message(chat_id, text, reply_markup=None):
        url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id, 
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        
        try:
            response = requests.post(
                url, 
                json=payload, 
                timeout=Config.REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            return False

class DataStorage:
    @staticmethod
    @handle_errors
    @retry(max_attempts=Config.MAX_RETRIES)
    def get_thread_id(chat_id):
        headers = {"X-Master-Key": Config.JSONBIN_API_KEY}
        try:
            response = requests.get(
                Config.JSONBIN_URL, 
                headers=headers, 
                timeout=Config.REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                data = response.json().get("record", {})
                return data.get(str(chat_id))
            else:
                logger.error(f"JSONBin get error: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка получения thread_id: {e}")
            return None

    @staticmethod
    @handle_errors
    @retry(max_attempts=Config.MAX_RETRIES)
    def save_thread_id(chat_id, thread_id):
        headers = {
            "X-Master-Key": Config.JSONBIN_API_KEY,
            "Content-Type": "application/json"
        }
        
        try:
            # Получаем текущие данные
            response = requests.get(
                Config.JSONBIN_URL, 
                headers=headers, 
                timeout=Config.REQUEST_TIMEOUT
            )
            data = response.json().get("record", {}) if response.status_code == 200 else {}
            
            # Обновляем данные
            data[str(chat_id)] = thread_id
            
            # Сохраняем
            response = requests.put(
                Config.JSONBIN_URL, 
                headers=headers, 
                json=data, 
                timeout=Config.REQUEST_TIMEOUT
            )
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка сохранения thread_id: {e}")
            return False

    @staticmethod
    @handle_errors
    @retry(max_attempts=Config.MAX_RETRIES)
    def reset_thread_id(chat_id):
        headers = {
            "X-Master-Key": Config.JSONBIN_API_KEY,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(
                Config.JSONBIN_URL, 
                headers=headers, 
                timeout=Config.REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                data = response.json().get("record", {})
                if str(chat_id) in data:
                    del data[str(chat_id)]
                    response = requests.put(
                        Config.JSONBIN_URL, 
                        headers=headers, 
                        json=data, 
                        timeout=Config.REQUEST_TIMEOUT
                    )
                    return response.status_code == 200
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка сброса thread_id: {e}")
            return False

class FileManager:
    @staticmethod
    @handle_errors
    def get_text_content(filename):
        """Получение содержимого текстовых файлов"""
        try:
            with open(f"texts/{filename}.txt", "r", encoding="utf-8") as f:
                content = f.read().strip()
                return content if content else "📄 Содержимое файла пустое."
        except FileNotFoundError:
            logger.warning(f"Файл texts/{filename}.txt не найден")
            return "📄 Содержимое временно недоступно. Попробуйте позже."
        except Exception as e:
            logger.error(f"Ошибка чтения файла {filename}: {e}")
            return "❌ Ошибка загрузки содержимого."

class OpenAIAssistant:
    @staticmethod
    def get_headers():
        return {
            "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
            "OpenAI-Beta": "assistants=v2",
            "Content-Type": "application/json"
        }

    @staticmethod
    @handle_errors
    def create_thread():
        try:
            response = requests.post(
                "https://api.openai.com/v1/threads",
                headers=OpenAIAssistant.get_headers(),
                timeout=Config.REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                return response.json()["id"]
            else:
                logger.error(f"OpenAI thread creation error: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка создания thread: {e}")
            return None

    @staticmethod
    @handle_errors
    def send_message_to_thread(thread_id, message):
        payload = {"role": "user", "content": message}
        try:
            response = requests.post(
                f"https://api.openai.com/v1/threads/{thread_id}/messages",
                headers=OpenAIAssistant.get_headers(),
                json=payload,
                timeout=Config.REQUEST_TIMEOUT
            )
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка отправки сообщения в thread: {e}")
            return False

    @staticmethod
    @handle_errors
    def run_assistant(thread_id):
        payload = {"assistant_id": Config.ASSISTANT_ID}
        try:
            response = requests.post(
                f"https://api.openai.com/v1/threads/{thread_id}/runs",
                headers=OpenAIAssistant.get_headers(),
                json=payload,
                timeout=Config.REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                return response.json()["id"]
            else:
                logger.error(f"OpenAI run creation error: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запуска ассистента: {e}")
            return None

    @staticmethod
    @handle_errors
    def wait_for_completion(thread_id, run_id):
        for attempt in range(Config.OPENAI_WAIT_TIMEOUT):
            try:
                response = requests.get(
                    f"https://api.openai.com/v1/threads/{thread_id}/runs/{run_id}",
                    headers=OpenAIAssistant.get_headers(),
                    timeout=Config.REQUEST_TIMEOUT
                )
                if response.status_code == 200:
                    status = response.json().get("status")
                    if status == "completed":
                        return True
                    elif status in ["failed", "cancelled", "expired"]:
                        logger.error(f"Выполнение завершилось со статусом: {status}")
                        return False
                time.sleep(1)
            except requests.exceptions.RequestException as e:
                logger.error(f"Ошибка проверки статуса: {e}")
                time.sleep(2)
        
        logger.warning("Превышено время ожидания выполнения OpenAI")
        return False

    @staticmethod
    @handle_errors
    def get_assistant_response(thread_id):
        try:
            response = requests.get(
                f"https://api.openai.com/v1/threads/{thread_id}/messages",
                headers=OpenAIAssistant.get_headers(),
                timeout=Config.REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                messages = response.json().get("data", [])
                for msg in messages:
                    if msg["role"] == "assistant":
                        return msg["content"][0]["text"]["value"]
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка получения ответа: {e}")
            return None

class MessageHandler:
    @staticmethod
    def handle_start_command(chat_id):
        welcome_text = (
            "👋 <b>Добро пожаловать в EmpathAI!</b>\n\n"
            "Я твой виртуальный помощник для поддержки, саморазвития и снижения тревожности.\n\n"
            "📋 Выбери пункт из меню, чтобы начать общение."
        )
        TelegramAPI.send_message(chat_id, welcome_text, reply_markup=TelegramAPI.main_menu())

    @staticmethod
    def handle_reset_command(chat_id):
        # Сначала показываем содержимое reset.txt
        reset_content = FileManager.get_text_content("reset")
        TelegramAPI.send_message(chat_id, reset_content)
        
        # Затем сбрасываем диалог
        if DataStorage.reset_thread_id(chat_id):
            TelegramAPI.send_message(
                chat_id, 
                "✅ Диалог успешно сброшен. Начнем заново?", 
                reply_markup=TelegramAPI.main_menu()
            )
        else:
            TelegramAPI.send_message(
                chat_id, 
                "❌ Ошибка сброса диалога. Попробуйте позже.", 
                reply_markup=TelegramAPI.main_menu()
            )

    @staticmethod
    def handle_menu_commands(chat_id, text):
        filename_map = {
            "🧠 Инструкция": "support",
            "❓ Гид по боту": "faq",
            "💳 Купить подписку": "subscribe",
            "📜 Условия пользования": "rules",
            "ℹ️ Информация": "info",
            "🆓 Пробный период": "trial_info"
        }
        
        filename = filename_map.get(text)
        if filename:
            content = FileManager.get_text_content(filename)
            TelegramAPI.send_message(chat_id, content, reply_markup=TelegramAPI.main_menu())
            return True
        return False

    @staticmethod
    def handle_ai_conversation(chat_id, text):
        """Обработка AI диалога в отдельном потоке"""
        def process_ai_request():
            try:
                # Получаем или создаем thread
                thread_id = DataStorage.get_thread_id(chat_id)
                if not thread_id:
                    thread_id = OpenAIAssistant.create_thread()
                    if not thread_id:
                        TelegramAPI.send_message(
                            chat_id, 
                            "❌ Ошибка инициализации сессии. Попробуйте позже.", 
                            reply_markup=TelegramAPI.main_menu()
                        )
                        return
                    DataStorage.save_thread_id(chat_id, thread_id)

                # Отправляем сообщение в thread
                if not OpenAIAssistant.send_message_to_thread(thread_id, text):
                    TelegramAPI.send_message(
                        chat_id, 
                        "❌ Ошибка отправки сообщения. Попробуйте позже.", 
                        reply_markup=TelegramAPI.main_menu()
                    )
                    return

                # Запускаем ассистента
                run_id = OpenAIAssistant.run_assistant(thread_id)
                if not run_id:
                    TelegramAPI.send_message(
                        chat_id, 
                        "❌ Ошибка запуска AI-сессии. Попробуйте позже.", 
                        reply_markup=TelegramAPI.main_menu()
                    )
                    return

                # Ждем выполнения
                if not OpenAIAssistant.wait_for_completion(thread_id, run_id):
                    TelegramAPI.send_message(
                        chat_id, 
                        "⏳ Превышено время ожидания ответа. Попробуйте еще раз.", 
                        reply_markup=TelegramAPI.main_menu()
                    )
                    return

                # Получаем ответ
                response = OpenAIAssistant.get_assistant_response(thread_id)
                if response:
                    TelegramAPI.send_message(chat_id, response, reply_markup=TelegramAPI.main_menu())
                else:
                    TelegramAPI.send_message(
                        chat_id, 
                        "🤖 Не удалось получить ответ. Попробуйте еще раз.", 
                        reply_markup=TelegramAPI.main_menu()
                    )

            except Exception as e:
                logger.error(f"Ошибка в AI обработке для chat_id {chat_id}: {e}")
                TelegramAPI.send_message(
                    chat_id, 
                    "❌ Произошла ошибка. Попробуйте позже.", 
                    reply_markup=TelegramAPI.main_menu()
                )

        # Запускаем в отдельном потоке для неблокирующей обработки
        Thread(target=process_ai_request, daemon=True).start()

def handle_update(update):
    """Главная функция обработки обновлений"""
    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    
    logger.info(f"Получено сообщение от {chat_id}: {text[:50]}...")

    if text == "/start":
        MessageHandler.handle_start_command(chat_id)
    elif text == "🔄 Сбросить диалог":
        MessageHandler.handle_reset_command(chat_id)
    elif MessageHandler.handle_menu_commands(chat_id, text):
        pass  # Команда уже обработана
    elif text:  # Обычное сообщение для AI
        MessageHandler.handle_ai_conversation(chat_id, text)

# Flask маршруты
@app.route("/", methods=["GET"])
def health_check():
    """Health check для Render"""
    return jsonify({
        "status": "healthy",
        "service": "EmpathAI Bot",
        "timestamp": int(time.time()),
        "config_valid": validate_config()
    })

@app.route("/webhook", methods=["POST"])
def webhook():
    """Webhook endpoint для Telegram"""
    try:
        update = request.get_json()
        if not update:
            logger.warning("Получен пустой JSON")
            return jsonify({"error": "Invalid JSON"}), 400
            
        handle_update(update)
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"Ошибка webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/set_webhook", methods=["POST"])
def set_webhook():
    """Установка webhook (для отладки)"""
    try:
        data = request.get_json()
        webhook_url = data.get("url") if data else None
        
        if not webhook_url:
            return jsonify({"error": "URL not provided"}), 400
            
        url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/setWebhook"
        response = requests.post(url, json={"url": webhook_url}, timeout=10)
        
        return jsonify(response.json())
    except Exception as e:
        logger.error(f"Ошибка установки webhook: {e}")
        return jsonify({"error": str(e)}), 500

# Инициализация при запуске
if __name__ == "__main__":
    logger.info("Запуск EmpathAI Bot...")
    
    if not validate_config():
        logger.error("Ошибка конфигурации. Проверьте переменные окружения.")
        sys.exit(1)
    
    logger.info("Конфигурация валидна. Бот готов к работе.")
    
    # Для Render используем PORT из переменных окружения
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
