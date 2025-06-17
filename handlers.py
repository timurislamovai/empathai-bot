import os
import requests
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
ADMIN_IDS = [944583273,396497806]  # 🔁 Замени на свой Telegram ID из личного кабинета

bot = Bot(token=os.environ["TELEGRAM_TOKEN"])
FREE_MESSAGES_LIMIT = int(os.environ.get("FREE_MESSAGES_LIMIT", 50))


def main_menu():
    buttons = [
        [KeyboardButton("💳 Купить подписку")],
        [KeyboardButton("📜 Условия пользования"), KeyboardButton("❓ Гид по боту")],
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

        telegram_id = int(message["from"]["id"])
        text = message.get("text", "")
        chat_id = message["chat"]["id"]

        user = get_user_by_telegram_id(db, telegram_id)
        if not user:
            user = create_user(db, telegram_id)
            
        # === 👨‍💻 Обработка команды /admin_stats (только для админов) ===
        if text == "/admin_stats":
            if user.telegram_id not in ADMIN_IDS:
                bot.send_message(chat_id, "⛔️ У вас нет доступа к этой команде.")
            else:
                from utils import get_stats_summary
                stats = get_stats_summary(db)
                bot.send_message(chat_id, stats)
            return

        if text == "/start":
            bot.send_message(
                chat_id,
                "👋 Добро пожаловать!\n\n"
                "Привет, я Ила — твой виртуальный помощник в понимании себя и поиске душевного равновесия.\n\n"
                "🆓 На пробный период вам доступно 50 бесплатных сообщений.\n"
                "💳 После окончания лимита можно оформить подписку.\n\n"
                "📋 Выберите пункт меню или напишите свой вопрос, чтобы начать общение.",
                reply_markup=main_menu()
            )
            return


        if text == "🔄 Сбросить диалог":
            reset_user_thread(db, user)
            bot.send_message(chat_id, "Диалог сброшен. Можем начать сначала 🌀", reply_markup=main_menu())
            return

        # ==== 👤 Обработка кнопки "Личный кабинет" ====
# Показывает Telegram ID пользователя, использованные сообщения и статус пробного периода

        if text == "👤 Личный кабинет":
            remaining = max(0, FREE_MESSAGES_LIMIT - user.free_messages_used)
            reply = (
                f"👤 Личный кабинет\n"
                f"🆔 Ваш Telegram ID: {user.telegram_id}\n\n"
                f"💬 Сообщений использовано: {user.free_messages_used} из {FREE_MESSAGES_LIMIT}\n"
                f"📊 Осталось: {remaining}\n"
                f"📅 Пробный период: {'активен' if remaining > 0 else 'завершён'}"
            )
            bot.send_message(chat_id, reply, reply_markup=main_menu())
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

        # Проверка лимита
        if user.free_messages_used >= FREE_MESSAGES_LIMIT:
            bot.send_message(chat_id, "⚠️ Превышен лимит бесплатных сообщений.\nОформите подписку для продолжения.", reply_markup=main_menu())
            return

        # Получаем ответ от GPT (Assistant API)
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
