import os
import json
import requests
from flask import Flask, request, jsonify
from telegram import Bot, Update, ReplyKeyboardMarkup, KeyboardButton
import openai
from datetime import datetime, timedelta

app = Flask(__name__)

# Переменные окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID")
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")

# Инициализация бота
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Папка с текстами
TEXT_FOLDER = "texts"

# Функции для работы с JSONBin.io
def load_user_data(user_id):
    try:
        response = requests.get(
            f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest",
            headers={"X-Master-Key": JSONBIN_API_KEY}
        )
        response.raise_for_status()
        data = response.json()
        all_data = data.get("record", {})
        # Обрабатываем вложенные "record"
        while isinstance(all_data.get("record"), dict):
            all_data = all_data["record"]
        user_data = all_data.get(user_id, {
            "free_trial_start": None,
            "messages_today": 0,
            "last_message_date": None,
            "is_subscribed": False,
            "history": []
        })
        # Проверяем, если user_data — список (старая структура)
        if isinstance(user_data, list):
            print(f"[DEBUG] Обнаружен старый формат данных для user_id {user_id}, сбрасываем")
            user_data = {
                "free_trial_start": None,
                "messages_today": 0,
                "last_message_date": None,
                "is_subscribed": False,
                "history": user_data  # Сохраняем старую историю
            }
            save_user_data(user_id, user_data)
        print(f"[DEBUG] Загружены данные для user_id {user_id}: {json.dumps(user_data, ensure_ascii=False)}")
        return user_data
    except Exception as e:
        print(f"[!] Ошибка загрузки данных: {e}, Response: {response.text if 'response' in locals() else 'No response'}")
        return {"free_trial_start": None, "messages_today": 0, "last_message_date": None, "is_subscribed": False, "history": []}

def save_user_data(user_id, user_data):
    try:
        all_data = {user_id: user_data}  # Чистая структура
        print(f"[DEBUG] Отправляем в JSONBin.io: {json.dumps(all_data, ensure_ascii=False)}")
        update = requests.put(
            f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}",
            headers={
                "X-Master-Key": JSONBIN_API_KEY,
                "Content-Type": "application/json"
            },
            json=all_data
        )
        update.raise_for_status()
        print(f"[DEBUG] Успешно сохранено в JSONBin.io, Response: {update.text}")
        return True
    except Exception as e:
        print(f"[!] Ошибка сохранения данных: {e}, Response: {update.text if 'update' in locals() else 'No response'}")
        return False

def reset_user_data(user_id):
    user_data = {
        "free_trial_start": None,
        "messages_today": 0,
        "last_message_date": None,
        "is_subscribed": False,
        "history": []
    }
    save_user_data(user_id, user_data)

def reset_history(user_id):
    user_data = load_user_data(user_id)
    user_data["history"] = []
    save_user_data(user_id, user_data)

# Загрузка текстов для меню
def load_text(name):
    try:
        with open(f"{TEXT_FOLDER}/{name}.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Извините, информация временно недоступна."

# Проверка лимитов
def check_limits(user_id):
    user_data = load_user_data(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"[DEBUG] Проверка лимитов для user_id {user_id}, today: {today}")
    
    # Сброс счётчика сообщений, если новый день
    if user_data["last_message_date"] != today:
        user_data["messages_today"] = 0
        user_data["last_message_date"] = today
        save_user_data(user_id, user_data)
    
    # Проверка подписки
    if user_data["is_subscribed"]:
        return True, user_data, "Вы подписчик, лимитов нет! 😊", None
    
    # Проверка триала
    if user_data["free_trial_start"] is None:
        return False, user_data, "Получи 7 дней бесплатного периода (15 сообщений в день)! Нажми 🆓 Начать бесплатный период.", ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton("🆓 Начать бесплатный период")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    
    try:
        trial_start = datetime.strptime(user_data["free_trial_start"], "%Y-%m-%d")
        trial_end = trial_start + timedelta(days=7)
        if datetime.now() > trial_end:
            return False, user_data, "Твой бесплатный период закончился. 💳 Купить подписку?", ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton("💳 Купить подписку")]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        
        if user_data["messages_today"] >= 15:
            return False, user_data, f"Лимит 15 сообщений сегодня достигнут. 💳 Купить подписку? Триал до {trial_end.strftime('%Y-%m-%d')}.", ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton("💳 Купить подписку")]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        
        return True, user_data, f"Осталось {15 - user_data['messages_today']} сообщений сегодня.", None
    except ValueError as e:
        print(f"[!] Ошибка парсинга даты free_trial_start: {e}")
        user_data["free_trial_start"] = None
        save_user_data(user_id, user_data)
        return False, user_data, "Ошибка с триалом. Нажми 🆓 Начать бесплатный период.", ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton("🆓 Начать бесплатный период")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )

# Генерация ответа через Open AI
def generate_response(user_id, message_text):
    if not message_text or message_text.strip() == "":
        return "Пожалуйста, напиши что-нибудь, чтобы я мог ответить! 😊", None
    
    can_respond, user_data, limit_message, custom_menu = check_limits(user_id)
    print(f"[DEBUG] generate_response: can_respond={can_respond}, limit_message={limit_message}")
    if not can_respond:
        return limit_message, custom_menu
    
    history = user_data["history"]
    history.append({"role": "user", "content": message_text})
    user_data["history"] = history[-10:]  # Ограничение истории
    user_data["messages_today"] += 1
    save_user_data(user_id, user_data)
    
    print(f"[DEBUG] История перед отправкой в Open AI: {json.dumps(history, ensure_ascii=False)}")
    openai.api_key = OPENAI_API_KEY
    try:
        thread = openai.beta.threads.create()
        thread_id = thread.id
        print(f"[DEBUG] Создан thread_id: {thread_id}")

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
        print(f"[DEBUG] Создан run_id: {run.id}")

        while True:
            status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            print(f"[DEBUG] Статус run: {status.status}")
            if status.status == "completed":
                break
            elif status.status in ["failed", "cancelled", "expired"]:
                return f"Извините, произошла ошибка (status: {status.status}). Попробуйте позже.", None

        messages = openai.beta.threads.messages.list(thread_id=thread_id)
        reply = ""
        for msg in reversed(messages.data):
            if msg.role == "assistant":
                reply = msg.content[0].text.value
                break

        history.append({"role": "assistant", "content": reply})
        user_data["history"] = history[-10:]
        save_user_data(user_id, user_data)
        print(f"[DEBUG] Ответ от Open AI: {reply}")
        return f"{reply}\n\n{limit_message}", None
    except Exception as e:
        print(f"[!] Ошибка Open AI: {e}")
        return "Извините, что-то пошло не так. Попробуйте ещё раз!", None

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

# Меню для новых пользователей
trial_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("🆓 Начать бесплатный период")],
        [KeyboardButton("🧠 Инструкция"), KeyboardButton("ℹ️ О Сервисе")],
        [KeyboardButton("🔄 Сбросить диалог"), KeyboardButton("📜 Пользовательское соглашение")],
        [KeyboardButton("❓ Гид по боту")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

@app.route(f"/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    if not update or not update.effective_chat:
        return jsonify({"status": "error", "message": "Invalid update"})

    chat_id = str(update.effective_chat.id)
    text = update.message.text.strip() if update.message and update.message.text else ""

    user_data = load_user_data(chat_id)
    print(f"[DEBUG] User data: {json.dumps(user_data, ensure_ascii=False)}")
    
    menu = trial_menu if not user_data.get("free_trial_start") else main_menu

    if text == "/start":
        reset_user_data(chat_id)
        welcome = (
            "Привет! Я Ила — твой виртуальный психолог и наставник по саморазвитию.\n\n"
            "Получи 7 дней бесплатного периода (15 сообщений в день)! Нажми 🆓 Начать бесплатный период или напиши мне."
        )
        bot.send_message(chat_id=chat_id, text=welcome, reply_markup=trial_menu)
    elif text == "🆓 Начать бесплатный период":
        if not user_data.get("free_trial_start"):
            user_data["free_trial_start"] = datetime.now().strftime("%Y-%m-%d")
            user_data["last_message_date"] = datetime.now().strftime("%Y-%m-%d")
            user_data["messages_today"] = 0
            if save_user_data(chat_id, user_data):
                bot.send_message(chat_id=chat_id, text="Бесплатный период начался! 7 дней, 15 сообщений в день. Пиши мне!", reply_markup=main_menu)
            else:
                bot.send_message(chat_id=chat_id, text="Ошибка при запуске триала. Попробуй ещё раз!", reply_markup=menu)
        else:
            bot.send_message(chat_id=chat_id, text="Твой бесплатный период уже активен!", reply_markup=main_menu)
    elif text == "💳 Купить подписку":
        bot.send_message(chat_id=chat_id, text="Подписка пока в разработке. Напиши, чтобы продолжить!", reply_markup=main_menu)
    elif text == "🧠 Инструкция":
        bot.send_message(chat_id=chat_id, text=load_text("support"), reply_markup=menu)
    elif text == "ℹ️ О Сервисе":
        bot.send_message(chat_id=chat_id, text=load_text("info"), reply_markup=menu)
    elif text == "📜 Пользовательское соглашение":
        bot.send_message(chat_id=chat_id, text=load_text("rules"), reply_markup=menu)
    elif text == "❓ Гид по боту":
        bot.send_message(chat_id=chat_id, text=load_text("faq"), reply_markup=menu)
    elif text == "🔄 Сбросить диалог":
        reset_history(chat_id)
        bot.send_message(chat_id=chat_id, text=load_text("reset"), reply_markup=main_menu)
    else:
        answer, custom_menu = generate_response(chat_id, text)
        bot.send_message(chat_id=chat_id, text=answer, reply_markup=custom_menu or menu)

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True)
