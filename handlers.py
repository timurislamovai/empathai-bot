import os
import requests
from models import User
from referral import generate_cabinet_message, generate_withdraw_info
from telegram import Bot, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from utils import clean_markdown
from fastapi import Request
from database import SessionLocal
from models import (
    get_user_by_telegram_id,
    create_user,
    update_user_thread_id,
    increment_message_count,
    reset_user_thread
)
from openai_api import send_message_to_assistant

# ✅ Telegram ID админов, которым разрешена команда /admin_stats
ADMIN_IDS = ["944583273", "396497806"]

bot = Bot(token=os.environ["TELEGRAM_TOKEN"])
FREE_MESSAGES_LIMIT = int(os.environ.get("FREE_MESSAGES_LIMIT", 50))

def main_menu():
    buttons = [
        [KeyboardButton("💳 Купить подписку")],
        [KeyboardButton("📜 Условия пользования"), KeyboardButton("❓ Гид по боту")],
        [KeyboardButton("🔄 Сбросить диалог"), KeyboardButton("👤 Личный кабинет")],
        [KeyboardButton("🤝 Партнёрская программа")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

async def handle_update(update: dict):
    print("👉 START handle_update")
    print("📦 update:", update)

    db = SessionLocal()
    try:
        if "callback_query" in update:
            query = update["callback_query"]
            data = query["data"]
            chat_id = query["message"]["chat"]["id"]
            telegram_id = str(query["from"]["id"])

            feedback_responses = {
                "feedback_good": "Рад это слышать! 😊",
                "feedback_neutral": "Спасибо, что делишься. Я рядом 🙏",
                "feedback_bad": "Сочувствую. Пожалуйста, береги себя. Я здесь 💙"
            }

            if data in feedback_responses:
                bot.answer_callback_query(callback_query_id=query["id"])
                bot.send_message(chat_id, feedback_responses[data])
                return

            if data == "withdraw_request":
                user = get_user_by_telegram_id(db, telegram_id)
                if not user:
                    bot.send_message(chat_id, "Ошибка: пользователь не найден.")
                    return
                message_text, markup = generate_withdraw_info(user, telegram_id)
                bot.send_message(chat_id, message_text, reply_markup=markup)
                return

        message = update.get("message")
        if message:
            text = message.get("text", "")
            chat_id = message["chat"]["id"]
            telegram_id = str(message["from"]["id"])
            user = get_user_by_telegram_id(db, telegram_id)

            if not user:
                user = create_user(db, telegram_id)

            # Обработка меню
            if text == "❓ Гид по боту":
                try:
                    with open("texts/guide.txt", "r", encoding="utf-8") as f:
                        bot.send_message(chat_id, f.read())
                except:
                    bot.send_message(chat_id, "⚠️ Гид недоступен.")
                return

            elif text == "📜 Условия пользования":
                try:
                    with open("texts/rules.txt", "r", encoding="utf-8") as f:
                        bot.send_message(chat_id, f.read())
                except:
                    bot.send_message(chat_id, "⚠️ Условия недоступны.")
                return

            elif text == "👤 Личный кабинет":
                message_text = generate_cabinet_message(user, telegram_id, db)
                bot.send_message(chat_id, message_text)
                return

            elif text == "🔄 Сбросить диалог":
                reset_user_thread(db, user)
                update_user_thread_id(db, user, None)
                bot.send_message(chat_id, "🧠 Диалог сброшен. Ты можешь начать сначала.")
                return

            # Обработка команды от администратора
            if text.startswith("/give_unlimited"):
                if telegram_id not in ADMIN_IDS:
                    bot.send_message(chat_id, "⛔ У вас нет доступа к этой команде.")
                    return
                parts = text.strip().split()
                if len(parts) != 2:
                    bot.send_message(chat_id, "⚠️ Использование: /give_unlimited <telegram_id>")
                    return
                target_id = parts[1]
                target_user = get_user_by_telegram_id(db, target_id)
                if target_user:
                    target_user.is_unlimited = True
                    db.commit()
                    bot.send_message(chat_id, f"✅ Пользователю {target_id} выдан безлимит.")
                    return

            # Проверка на кризисные слова
            from diagnostics import diagnose_topic, contains_crisis_words
            if contains_crisis_words(text):
                bot.send_message(chat_id, "Похоже, ты переживаешь непростой момент. "
                                          "Если тебе срочно нужна помощь — обратись в службу поддержки или к специалисту.")
                return

            # Диагностика темы
            diagnosed_question = diagnose_topic(text)
            if diagnosed_question:
                bot.send_message(chat_id, diagnosed_question)

            # Отправка в Assistant API
            try:
                response, thread_id = send_message_to_assistant(user.thread_id, text)
                if not user.thread_id:
                    update_user_thread_id(db, user, thread_id)
            except Exception as e:
                if "run is already active" in str(e).lower():
                    update_user_thread_id(db, user, None)
                    response, thread_id = send_message_to_assistant(None, text)
                else:
                    raise e

            increment_message_count(db, user)
            user = get_user_by_telegram_id(db, telegram_id)

            response = clean_markdown(response)
            bot.send_message(chat_id, response, reply_markup=main_menu())

            if user.total_messages % 5 == 0:
                feedback_question = "Как ты себя сейчас чувствуешь?"
                feedback_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("😊 Хорошо", callback_data="feedback_good")],
                    [InlineKeyboardButton("😐 Нейтрально", callback_data="feedback_neutral")],
                    [InlineKeyboardButton("😢 Плохо", callback_data="feedback_bad")]
                ])
                bot.send_message(chat_id, feedback_question, reply_markup=feedback_keyboard)

    finally:
        db.close()
