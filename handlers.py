import os
import requests
from telegram import Bot, ReplyKeyboardMarkup, KeyboardButton
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

bot = Bot(token=os.environ["TELEGRAM_TOKEN"])
FREE_MESSAGES_LIMIT = int(os.environ.get("FREE_MESSAGES_LIMIT", 50))


def main_menu():
    buttons = [
        [KeyboardButton("❓ Гид по боту")],
        [KeyboardButton("📜 Условия пользования"), KeyboardButton("💳 Купить подписку")],
        [KeyboardButton("🔄 Сбросить диалог"), KeyboardButton("👤 Личный кабинет")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


async def handle_update(update: dict):
    print("✅ Webhook получен от Telegram")
    print("📦 update:", update)

    db = SessionLocal()
    try:
        message = update.get("message")
        if not message:
            print("⚠️ Нет поля 'message'")
            return

        telegram_id = str(message["from"]["id"])
        text = message.get("text", "")
        chat_id = message["chat"]["id"]

        user = get_user_by_telegram_id(db, telegram_id)
        if not user:
            user = create_user(db, telegram_id)

        if text == "🔄 Сбросить диалог":
            reset_user_thread(db, user)
            bot.send_message(chat_id, "Диалог сброшен. Можем начать сначала 🌀", reply_markup=main_menu())
            return

        if text == "👤 Личный кабинет":
            remaining = max(0, FREE_MESSAGES_LIMIT - user.free_messages_used)
            bot.send_message(
                chat_id,
                f"🧾 Вы использовали {user.free_messages_used} из {FREE_MESSAGES_LIMIT} сообщений.\nОсталось: {remaining}",
                reply_markup=main_menu()
            )
            return

        if text in ["❓ Гид по боту", "📜 Условия пользования", "💳 Купить подписку"]:
            filename = {
                ""❓ Гид по боту": "faq.txt",
                "📜 Условия пользования": "rules.txt",
                "💳 Купить подписку": "subscribe.txt"
            }[text]
            try:
                with open(f"texts/{filename}", "r", encoding="utf-8") as f:
                    response = f.read()
            except FileNotFoundError:
                response = "Файл с информацией пока не загружен."
            bot.send_message(chat_id, response, reply_markup=main_menu())
            return

        # Проверка лимита
        if user.free_messages_used >= FREE_MESSAGES_LIMIT:
            bot.send_message(chat_id, "⚠️ Превышен лимит бесплатных сообщений.\nОформите подписку для продолжения.", reply_markup=main_menu())
            return

        # Получаем ответ от GPT (Assistant API)
        assistant_response, thread_id = send_message_to_assistant(user.thread_id, text)

        if not user.thread_id:
            update_user_thread_id(db, user, thread_id)

        increment_message_count(db, user)

        bot.send_message(chat_id, assistant_response, reply_markup=main_menu())

    except Exception as e:
        print("❌ Ошибка в handle_update:", e)

    finally:
        db.close()
