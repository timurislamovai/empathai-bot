import os
import json
import requests
import logging
from flask import Flask, request, jsonify
from telegram import Bot, Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Dispatcher
import openai

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Переменные окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID")
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")

# Инициализация бота
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

# Папка с текстами
TEXT_FOLDER = "texts"

# Функции для работы с JSONBin.io
def load_history(user_id):
    try:
        response = requests.get(
            f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest",
            headers={"X-Master-Key": JSONBIN_API_KEY}
        )
        response.raise_for_status()
        all_data = response.json().get("record", {})
        user_data = all_data.get(user_id, [])
        if isinstance(user_data, list):
            return user_data
        else:
            logger.warning(f"История пользователя {user_id} не список, сбрасываю.")
            return []
    except Exception as e:
        logger.error(f"Ошибка загрузки истории для {user_id}: {e}")
        return []

def save_history(user_id, history):
    try:
        history = history[-10:] if len(history) > 10 else history
        all_data = {user_id: history}
        logger.debug(f"Отправляем в JSONBin.io: {json.dumps(all_data, ensure_ascii=False)}")
        logger.debug(f"URL: https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}")
        update = requests.put(
            f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}",
            headers={
                "X-Master-Key": JSONBIN_API_KEY,
                "Content-Type": "application/json"
            },
            json={"record": all_data}
        )
        update.raise_for_status()
        logger.info(f"Успешно сохранено в JSONBin.io для {user_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения истории для {user_id}: {e}, Response: {update.text if 'update' in locals() else 'No response'}")
        return False

def reset_history(user_id):
    save_history(user_id, [])

# Загрузка текстов для меню
def load_text(name):
    try:
        with open(f"{TEXT_FOLDER}/{name}.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning(f"Файл {TEXT_FOLDER}/{name}.txt не найден")
        return "Извините, информация временно недоступна."

# Генерация ответа через Open AI
def generate_response(user_id, message_text):
    if not message_text or message_text.strip() == "":
        return "Пожалуйста, напиши что-нибудь, чтобы я мог ответить! 😊"
    
    history = load_history(user_id)
    history.append({"role": "user", "content": message_text})
    logger.debug(f"История перед отправкой в Open AI для {user_id}: {json.dumps(history, ensure_ascii=False)}")

    openai.api_key = OPENAI_API_KEY
    try:
        thread = openai.beta.threads.create()
        thread_id = thread.id
        logger.info(f"Создан thread_id: {thread_id} для {user_id}")

        for msg in history:
            if not msg["content"] or msg["content"].strip() == "":
                continue
            openai.beta.threads.messages.create(
                thread_id=thread_id,
                role=msg["role"],
                content=msg["content"]
            )

        run = openai.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        logger.info(f"Создан run_id: {run.id} для {user_id}")

        while True:
            status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            logger.debug(f"Статус run для {user_id}: {status.status}")
            if status.status == "completed":
                break
            elif status.status in ["failed", "cancelled", "expired"]:
                return f"Извините, произошла ошибка (status: {status.status}). Попробуйте позже."

        messages = openai.beta.threads.messages.list(thread_id=thread_id)
        reply = ""
        for msg in reversed(messages.data):
            if msg.role == "assistant":
                reply = msg.content[0].text.value
                break

        history.append({"role": "assistant", "content": reply})
        save_history(user_id, history)
        logger.info(f"Ответ от Open AI для {user_id}: {reply}")
        return reply
    except Exception as e:
        logger.error(f"Ошибка Open AI для {user_id}: {e}")
        return "Извините, что-то пошло не так. Попробуйте ещё раз!"

# Нижнее меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("🧠 Инструкция"), KeyboardButton("ℹ️ О Сервисе")],
        [KeyboardButton("🔄 Сбросить диалог"), KeyboardButton("📜 Пользовательское соглашение")],
        [KeyboardButton("❓ Гид по боту")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# Инлайн-кнопка для подтверждения согласия
def get_agreement_inline_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Продолжить", callback_data="agree")]
    ])

@app.route(f"/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    if not update or not update.effective_chat:
        logger.error("Получено некорректное обновление")
        return jsonify({"status": "error", "message": "Invalid update"})

    chat_id = str(update.effective_chat.id)
    
    # Обработка инлайн-кнопки
    if update.callback_query:
        query = update.callback_query
        query.answer()
        if query.data == "agree":
            history = load_history(chat_id)
            history.append({"role": "user", "content": "Пользователь подтвердил согласие с пользовательским соглашением"})
            save_history(chat_id, history)
            logger.info(f"Пользователь {chat_id} подтвердил согласие")
            bot.send_message(
                chat_id=chat_id,
                text="Спасибо за подтверждение! Вы можете продолжать пользоваться ботом.",
                reply_markup=main_menu
            )
        return jsonify({"status": "ok"})

    text = update.message.text.strip() if update.message and update.message.text else ""
    logger.debug(f"Получено сообщение от {chat_id}: {text}")

    if text == "/start":
        welcome = (
            "Привет! Я Ила — твой виртуальный психолог и наставник по саморазвитию.\n\n"
            "Я здесь, чтобы помочь справляться с тревогой, стрессом и найти ответы на важные вопросы.\n\n"
            "Нажимая 'Продолжить', вы подтверждаете, что ознакомились с условиями пользовательского соглашения.\n"
            "Ознакомиться с ним можно по кнопке '📜 Пользовательское соглашение' в меню."
        )
        bot.send_message(
            chat_id=chat_id,
            text=welcome,
            reply_markup=get_agreement_inline_keyboard()
        )
        bot.send_message(
            chat_id=chat_id,
            text="Выберите пункт меню или напишите мне.",
            reply_markup=main_menu
        )
        logger.info(f"Отправлено приветственное сообщение для {chat_id}")
    elif text == "🧠 Инструкция":
        bot.send_message(chat_id=chat_id, text=load_text("support"), reply_markup=main_menu)
        logger.info(f"Отправлена инструкция для {chat_id}")
    elif text == "ℹ️ О Сервисе":
        bot.send_message(chat_id=chat_id, text=load_text("info"), reply_markup=main_menu)
        logger.info(f"Отправлена информация о сервисе для {chat_id}")
    elif text == "📜 Пользовательское соглашение":
        bot.send_message(chat_id=chat_id, text=load_text("rules"), reply_markup=main_menu)
        logger.info(f"Отправлено пользовательское соглашение для {chat_id}")
    elif text == "❓ Гид по боту":
        bot.send_message(chat_id=chat_id, text=load_text("faq"), reply_markup=main_menu)
        logger.info(f"Отправлен гид по боту для {chat_id}")
    elif text == "🔄 Сбросить диалог":
        reset_history(chat_id)
        bot.send_message(chat_id=chat_id, text=load_text("reset"), reply_markup=main_menu)
        logger.info(f"Сброшена история диалога для {chat_id}")
    else:
        answer = generate_response(chat_id, text)
        bot.send_message(chat_id=chat_id, text=answer, reply_markup=main_menu)
        logger.info(f"Отправлен ответ от Open AI для {chat_id}: {answer}")

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True)
