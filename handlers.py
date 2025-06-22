import os
import requests
from models import User
from admin_commands import give_unlimited
from referral import generate_cabinet_message, generate_withdraw_info
from telegram import Bot, ReplyKeyboardMarkup, KeyboardButton
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
ADMIN_IDS = ["944583273", "396497806"]  # 🔁 Замени на свой Telegram ID из личного кабинета

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
                else:
                    bot.send_message(chat_id, "❌ Пользователь не найден.")
                return

            chat_id = message["chat"]["id"]
            telegram_id = str(message["from"]["id"])
            user = get_user_by_telegram_id(db, telegram_id)

            if text in ["👤 Личный кабинет", "👥 Кабинет", "Личный кабинет"]:
                user = get_user_by_telegram_id(db, telegram_id)
                if not user:
                    bot.send_message(chat_id, "Пользователь не найден.")
                    return
                message_text, markup = generate_cabinet_message(user, telegram_id, db)
                bot.send_message(chat_id, message_text, reply_markup=main_menu())
                return

            # --- Реферальный старт ---
            ref_code = None
            if text.startswith("/start"):
                parts = text.split(" ", 1)
                if len(parts) > 1:
                    ref_code = parts[1].strip()
                    print(f"⚡ Старт с рефкодом: {ref_code}")

                if not user:
                    print(f"👤 Новый пользователь. Telegram ID: {telegram_id}, рефкод: {ref_code}")
                    user = create_user(db, telegram_id, referrer_code=ref_code)
                    BONUS_AMOUNT = 100.0
                    if ref_code:
                        inviter = db.query(User).filter(User.telegram_id == ref_code).first()
                        if inviter:
                            inviter.balance += BONUS_AMOUNT
                            inviter.total_earned += BONUS_AMOUNT
                            db.commit()
                            print(f"✅ Начислено {BONUS_AMOUNT} пригласившему: {ref_code}")

                bot.send_message(
                    chat_id,
                    "👋 Добро пожаловать!\n\n"
                    "Привет, я Ила — твой личный виртуальный психолог и наставник по саморазвитию.\n\n"
                    "🆓 Вам доступно 50 бесплатных сообщений.\n"
                    "💳 После окончания лимита можно оформить подписку.\n\n"
                    "📋 Выберите пункт меню или напишите свой вопрос.",
                    reply_markup=main_menu()
                )
                return

            # --- Команды ---
            if text == "/admin_stats" and user.telegram_id in ADMIN_IDS:
                from utils import get_stats_summary
                stats = get_stats_summary(db)
                bot.send_message(chat_id, stats)
                return

            if text == "/admin_referrals" and user.telegram_id in ADMIN_IDS:
                from admin_commands import handle_admin_stats
                handle_admin_stats(db, chat_id, bot)
                return

            if text in ["👤 Личный кабинет", "👥 Кабинет", "Личный кабинет"]:
                message_text, markup = generate_cabinet_message(user, telegram_id, db)
                bot.send_message(chat_id, message_text, reply_markup=markup)
                return

            if text == "🤝 Партнёрская программа":
                message_text, markup = generate_withdraw_info(user, telegram_id)
                bot.send_message(chat_id, message_text, reply_markup=main_menu())
                return

            if text in ["💳 Купить подписку", "📜 Условия пользования", "❓ Гид по боту"]:
                filename = {
                    "💳 Купить подписку": "subscribe.txt",
                    "❓ Гид по боту": "guide.txt",
                    "📜 Условия пользования": "rules.txt"
                }[text]
                try:
                    with open(f"texts/{filename}", "r", encoding="utf-8") as f:
                        response = f.read()
                except FileNotFoundError:
                    response = "Файл с информацией пока не загружен."
                bot.send_message(chat_id, response, reply_markup=main_menu())
                return

            # --- Проверка лимита ---
            if not user.is_unlimited:
                if user.free_messages_used >= FREE_MESSAGES_LIMIT:
                    bot.send_message(
                        chat_id,
                        "⚠️ Превышен лимит бесплатных сообщений.\nОформите подписку для продолжения.",
                        reply_markup=main_menu()
                    )
                    return


            # --- Assistant API (OpenAI) ---
            try:
                assistant_response, thread_id = send_message_to_assistant(user.thread_id, text)
            except Exception as e:
                if "run is active" in str(e):
                    print("⚠️ Предыдущий run ещё выполняется. Сбрасываю thread.")
                    user.thread_id = None
                    db.commit()
                    assistant_response, thread_id = send_message_to_assistant(None, text)
                else:
                    raise e

            if not user.thread_id:
                update_user_thread_id(db, user, thread_id)

            increment_message_count(db, user)
            assistant_response = clean_markdown(assistant_response)
            bot.send_message(chat_id, assistant_response, reply_markup=main_menu())

    except Exception as e:
        print("❌ Ошибка в handle_update:", e)
    finally:
        db.close()
