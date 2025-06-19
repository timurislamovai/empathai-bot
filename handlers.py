import os
import requests
from models import User
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
        [KeyboardButton("🔄 Сбросить диалог"), KeyboardButton("👤 Личный кабинет")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


async def handle_update(update: dict):
    print("👉 START handle_update")
    print("✅ Webhook получен от Telegram")
    print("📦 update:", update)

    db = SessionLocal()
    try:
        # === 1. Обработка inline-кнопок (callback_query) ===
        if "callback_query" in update:
                query = update["callback_query"]
                data = query["data"]
                chat_id = query["message"]["chat"]["id"]
                telegram_id = str(query["from"]["id"])

        if data == "withdraw_request":
            if data == "withdraw_request":
                print("💵 Обрабатываем вывод")
                user = get_user_by_telegram_id(db, telegram_id)
            if user is None:
                bot.send_message(chat_id, "Ошибка: пользователь не найден.")
                return
        
            message_text, markup = generate_withdraw_info(user, telegram_id)
            bot.send_message(chat_id, message_text, reply_markup=markup)
            return


        # === 2. Обычные сообщения (текстовые) ===
        message = update.get("message")
        if message:
            print("📩 Получено обычное сообщение")
            text = message.get("text", "")
            chat_id = message["chat"]["id"]
            telegram_id = str(message["from"]["id"])
            user = get_user_by_telegram_id(db, telegram_id)
        
            # --- Обработка команды /start с реферальным кодом ---
            ref_code = None  # по умолчанию нет
            if text.startswith("/start"):
                parts = text.split(" ", 1)
                if len(parts) > 1:
                    ref_code = parts[1].strip()
                print(f"⚡ Старт с рефкодом: {ref_code}")
        
            # --- Личный кабинет ---
            if text == "👤 Личный кабинет":
                message_text, markup = generate_cabinet_message(user, telegram_id, db)
                bot.send_message(chat_id, message_text, reply_markup=markup)
                return
        
            # --- Заглушка: в будущем — Assistant API ---
            # from openai_api import assistant_api_reply
            # assistant_response = assistant_api_reply(user, text)
            # bot.send_message(chat_id, assistant_response)
            return



    except Exception as e:
        print("❌ Ошибка в handle_update:", e)
    finally:
        db.close()



        # --- Обработка команды /start с реферальным параметром ---
            ref_code = None  # по умолчанию реферальный код отсутствует
            if text.startswith("/start"):  # если сообщение начинается с команды /start
                parts = text.split(" ", 1)  # разделяем по пробелу на команду и параметр (если есть)
                if len(parts) > 1:
                    ref_code = parts[1].strip()  # берем параметр после /start как реферальный код

        # Проверяем, есть ли пользователь в базе
            user = get_user_by_telegram_id(db, telegram_id)
            if not user:
                print(f"👤 Новый пользователь. Telegram ID: {telegram_id}, рефкод: {ref_code}")
            # Если пользователя нет — создаём нового, передавая реферальный код (если он есть)
            user = create_user(db, telegram_id, referrer_code=ref_code)

            # === Начисление бонуса пригласившему ===
            BONUS_AMOUNT = 100.0  # Пока фиксированное значение
            
            if ref_code:
                inviter = db.query(User).filter(User.telegram_id == ref_code).first()
                if inviter:
                    inviter.balance += BONUS_AMOUNT
                    inviter.total_earned += BONUS_AMOUNT
                    db.commit()
                    print(f"✅ Начислено {BONUS_AMOUNT} пригласившему: {ref_code}")


            
        # === 👨‍💻 Обработка команды /admin_stats (только для админов) ===
        if text == "/admin_stats":
            if user.telegram_id not in ADMIN_IDS:
                bot.send_message(chat_id, "⛔️ У вас нет доступа к этой команде.")
            else:
                from utils import get_stats_summary
                stats = get_stats_summary(db)
                bot.send_message(chat_id, stats)
            return
            
        # 🔐 Обработка команды /admin_referrals (ТОП 10 пригласивших)
        # Показывает лидеров по количеству рефералов (реферальная статистика)
        elif text == "/admin_referrals":
            if user.telegram_id not in ADMIN_IDS:
                bot.send_message(chat_id, "⛔️ У вас нет доступа к этой команде.")
            else:
                from admin_commands import handle_admin_stats  # импорт функции из отдельного файла
                handle_admin_stats(db, chat_id, bot)  # вызываем обработчик статистики
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
        
        # ✅ Увеличиваем счётчик и обновляем дату через функцию
        increment_message_count(db, user)
        
        assistant_response = clean_markdown(assistant_response)
        bot.send_message(chat_id, assistant_response, reply_markup=main_menu())


   
