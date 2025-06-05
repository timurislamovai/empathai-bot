import os
import requests
from flask import Flask, request, jsonify
from telegram import Bot, Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
from telegram.utils.request import Request

import openai

app = Flask(__name__)

# Загрузка переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
JSONBIN_BIN_ID = os.getenv("JSONBIN_BIN_ID")
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")

openai.api_key = OPENAI_API_KEY

bot = Bot(token=TELEGRAM_BOT_TOKEN, request=Request(con_pool_size=8))

# Меню бота: команды с описаниями
MENU_COMMANDS = [
    {"command": "help", "description": "Инструкция по использованию"},
    {"command": "about", "description": "О проекте"},
    {"command": "reset", "description": "Сбросить диалог"},
    {"command": "terms", "description": "Условия использования"},
    {"command": "faq", "description": "Частые вопросы"},
]

# Кнопки меню для ReplyKeyboardMarkup (всегда показывать)
MENU_BUTTONS = [
    [KeyboardButton("Помощь"), KeyboardButton("О нас")],
    [KeyboardButton("Сбросить диалог"), KeyboardButton("Условия")],
    [KeyboardButton("Вопрос-ответ")],
]

# Функция установки меню в Telegram (вызывается один раз при старте)
def set_bot_menu():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setMyCommands"
    try:
        response = requests.post(url, json={"commands": MENU_COMMANDS})
        if response.status_code == 200:
            print("Меню Telegram установлено.")
        else:
            print("Не удалось установить меню:", response.text)
    except Exception as e:
        print("Ошибка при установке меню:", e)

# Вызываем сразу при старте приложения
set_bot_menu()

def get_user_history(user_id):
    """Получить историю пользователя из jsonbin.io"""
    headers = {"X-Master-Key": JSONBIN_API_KEY}
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            all_histories = data.get("record", {})
            return all_histories.get(str(user_id), [])
        else:
            print(f"Ошибка получения истории: {resp.text}")
    except Exception as e:
        print("Ошибка при get_user_history:", e)
    return []

def save_user_history(user_id, history):
    """Сохранить историю пользователя в jsonbin.io"""
    headers = {
        "Content-Type": "application/json",
        "X-Master-Key": JSONBIN_API_KEY,
    }
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
    # Получаем все истории, обновляем только текущего пользователя
    all_histories = {}
    try:
        resp = requests.get(f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest", headers=headers)
        if resp.status_code == 200:
            all_histories = resp.json().get("record", {})
    except Exception as e:
        print("Ошибка при чтении всех историй:", e)
    all_histories[str(user_id)] = history
    try:
        resp = requests.put(url, json=all_histories, headers=headers)
        if resp.status_code != 200:
            print(f"Ошибка сохранения истории: {resp.text}")
    except Exception as e:
        print("Ошибка при save_user_history:", e)

def load_text_from_github(filename):
    """Загружает текст из файла в репозитории GitHub (texts/filename)"""
    # Вставьте сюда ссылку на raw файл с вашим репозиторием и папкой texts
    # Пример: https://raw.githubusercontent.com/username/repo/main/texts/help.txt
    GITHUB_BASE_URL = "https://raw.githubusercontent.com/your_username/your_repo/main/texts/"
    url = GITHUB_BASE_URL + filename
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return r.text
        else:
            print(f"Ошибка загрузки файла {filename} с GitHub: {r.status_code}")
    except Exception as e:
        print(f"Ошибка загрузки файла {filename} с GitHub:", e)
    return "Извините, информация временно недоступна."

def generate_response(user_id, message_text):
    """Отправить сообщение в OpenAI Assistant API и получить ответ"""
    # Загрузка истории
    history = get_user_history(user_id)
    # Добавляем новое сообщение пользователя в историю
    history.append({"role": "user", "content": message_text})
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=history,
            user=str(user_id),
            # Если у вас ассистент с ID:
            # assistant_id=ASSISTANT_ID,
            # thread_id=None,
        )
        answer = response.choices[0].message["content"]
        # Добавляем ответ ассистента в историю
        history.append({"role": "assistant", "content": answer})
        # Сохраняем обновленную историю
        save_user_history(user_id, history)
        return answer
    except Exception as e:
        print("Ошибка OpenAI API:", e)
        return "Извините, произошла ошибка при обработке вашего запроса."

def get_welcome_message():
    return (
        "Привет! Меня зовут Ила — я виртуальный психолог и наставник по саморазвитию.\n\n"
        "Проект EmpathAI — AI-проект для осознанности и психологической поддержки.\n\n"
        "Как я могу помочь тебе сегодня? Если у тебя есть что-то на душе или вопросы, не стесняйся делиться. Я здесь, чтобы поддержать тебя."
    )

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    update = Update.de_json(data, bot)
    user_id = update.effective_user.id if update.effective_user else None
    
    if update.message:
        text = update.message.text
        
        # Проверяем команды меню
        if text == "/start":
            # Приветственное сообщение с меню
            bot.send_message(
                chat_id=update.effective_chat.id,
                text=get_welcome_message(),
                reply_markup=ReplyKeyboardMarkup(MENU_BUTTONS, resize_keyboard=True, one_time_keyboard=False)
            )
            return jsonify({"status": "ok"})
        
        elif text == "/reset" or text.lower() == "сбросить диалог":
            # Очистить историю
            save_user_history(user_id, [])
            # Загрузить текст из файла reset.txt
            reset_text = load_text_from_github("reset.txt")
            bot.send_message(
                chat_id=update.effective_chat.id,
                text=reset_text,
                reply_markup=ReplyKeyboardMarkup(MENU_BUTTONS, resize_keyboard=True, one_time_keyboard=False)
            )
            return jsonify({"status": "ok"})
        
        elif text.lower() in ["помощь", "/help"]:
            help_text = load_text_from_github("help.txt")
            bot.send_message(
                chat_id=update.effective_chat.id,
                text=help_text,
                reply_markup=ReplyKeyboardMarkup(MENU_BUTTONS, resize_keyboard=True, one_time_keyboard=False)
            )
            return jsonify({"status": "ok"})
        
        elif text.lower() in ["о нас", "about"]:
            about_text = load_text_from_github("about.txt")
            bot.send_message(
                chat_id=update.effective_chat.id,
                text=about_text,
                reply_markup=ReplyKeyboardMarkup(MENU_BUTTONS, resize_keyboard=True, one_time_keyboard=False)
            )
            return jsonify({"status": "ok"})
        
        elif text.lower() in ["условия", "terms"]:
            terms_text = load_text_from_github("terms.txt")
            bot.send_message(
                chat_id=update.effective_chat.id,
                text=terms_text,
                reply_markup=ReplyKeyboardMarkup(MENU_BUTTONS, resize_keyboard=True, one_time_keyboard=False)
            )
            return jsonify({"status": "ok"})
        
        elif text.lower() in ["вопрос-ответ", "faq"]:
            faq_text = load_text_from_github("faq.txt")
            bot.send_message(
                chat_id=update.effective_chat.id,
                text=faq_text,
                reply_markup=ReplyKeyboardMarkup(MENU_BUTTONS, resize_keyboard=True, one_time_keyboard=False)
            )
            return jsonify({"status": "ok"})
        
        else:
            # Основной диалог с ИИ
            answer = generate_response(user_id, text)
            bot.send_message(
                chat_id=update.effective_chat.id,
                text=answer,
                reply_markup=ReplyKeyboardMarkup(MENU_BUTTONS, resize_keyboard=True, one_time_keyboard=False)
            )
            return jsonify({"status": "ok"})
    
    return jsonify({"status": "no_message"})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
