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
    print("✅ Webhook получен от Telegram")
    print("📦 update:", update)

    db = SessionLocal()  # создаём сессию для работы с базой данных
    try:
        message = update.get("message")  # извлекаем объект сообщения из обновления
        if not message:
            print("⚠️ Нет поля 'message'")
            return  # если сообщение отсутствует — выходим из функции

        telegram_id = str(message["from"]["id"])  # получаем уникальный Telegram ID пользователя (строка)
        text = message.get("text", "")  # получаем текст сообщения, если есть
        chat_id = message["chat"]["id"]  # ID чата, куда нужно отправлять ответы

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

        # Далее логика обработки сообщения (твой текущий код)...

            
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
                    # Получаем пользователя из базы по Telegram ID
            user = get_user_by_telegram_id(db, telegram_id)
        
            if not user:
                # Если пользователь почему-то не найден
                bot.send_message(chat_id, "❌ Пользователь не найден.")
                return
        
            # --- Расчёт лимитов сообщений ---
            used = user.free_messages_used or 0
            limit = int(os.getenv("FREE_MESSAGES_LIMIT", 50))  # лимит из переменной окружения
            remaining = max(limit - used, 0)
        
            # --- Пробный период (можно сделать динамичным позже) ---
            trial_status = "активен"
        
            # --- Генерация реферальной ссылки ---
            # Автоматически подставляем username бота и telegram_id пользователя
            ref_link = f"https://t.me/{bot.get_me().username}?start={telegram_id}"
        
            # --- Формируем текст сообщения ---
            message = (
                f"👤 Личный кабинет\n"
                f"🆔 Ваш Telegram ID: {telegram_id}\n\n"
                f"💬 Сообщений использовано: {used} из {limit}\n"
                f"📊 Осталось: {remaining}\n"
                f"📅 Пробный период: {trial_status}\n\n"
                f"🔗 Ваша реферальная ссылка:\n{ref_link}\n"
                f"💰 Поделитесь ссылкой — и получайте доход!"
            )
        
            
            # --- Отправка сообщения пользователю ---
            bot.send_message(chat_id, message)
            return  # ← это обязательно! чтобы GPT не срабатывал дальше




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


    except Exception as e:
        print("❌ Ошибка в handle_update:", e)

    finally:
        db.close()
