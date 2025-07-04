import time
import os

from handlers.message_router import handle_command, handle_menu_button

from models import get_user_by_telegram_id, create_user
from database import SessionLocal
import os

from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.orm import Session

from referral import generate_cabinet_message, generate_withdraw_info
from admin_commands import handle_admin_stats, handle_admin_referrals, give_unlimited_access
from robokassa import generate_payment_url
from openai_api import reset_user_thread, send_message_to_assistant
from ui import main_menu, subscription_plan_keyboard
from utils import clean_markdown
from filters import classify_crisis_level, log_crisis_message
from datetime import datetime
from telegram import Bot

ADMIN_IDS = ["944583273", "396497806"]  # 🔁 Укажи своих админов
FREE_MESSAGES_LIMIT = int(os.environ.get("FREE_MESSAGES_LIMIT", 50))

bot = Bot(token=os.environ["TELEGRAM_TOKEN"])

def handle_update(update, db):
    message = update.get("message")
    if not message:
        return

    text = message.get("text", "")
    chat_id = message["chat"]["id"]
    telegram_id = str(message["from"]["id"])

    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
    user = create_user(db, telegram_id)
    
    if text.startswith("/"):
    handle_command(text, user, chat_id, bot, db)
    else:
    handle_menu_button(text, user, chat_id, bot, db)

def handle_command(text: str, user: User, chat_id: int, bot: Bot, db: Session):
    if text == "/admin_stats" and str(user.telegram_id) in ADMIN_IDS:
        handle_admin_stats(db, chat_id, bot)
        return

    if text == "/admin_referrals" and str(user.telegram_id) in ADMIN_IDS:
        handle_admin_referrals(db, chat_id, bot)
        return

    if text.startswith("/give_unlimited") and str(user.telegram_id) in ADMIN_IDS:
        give_unlimited_access(db, bot, chat_id, text)
        return

def handle_menu_button(text: str, user: User, chat_id: int, bot: Bot, db: Session):
    telegram_id = str(user.telegram_id)

    if text.startswith("/start"):
        parts = text.strip().split(" ", 1)
        ref_code = parts[1].strip() if len(parts) > 1 else None
    if ref_code and ref_code.startswith("ref"):
        ref_code = ref_code.replace("ref", "", 1)
    if ref_code and not ref_code.isdigit():
        ref_code = None

    if not user:
        user = create_user(db, telegram_id, referrer_code=ref_code)
    elif not user.referrer_code and ref_code:
        user.referrer_code = ref_code
        db.commit()

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


    if text == "💳 Купить подписку":
        bot.send_message(
            chat_id,
            "💡 _С EmpathAI ты получаешь поддержку каждый день — как от внимательного собеседника._\n\n"
            "🔹 *1 месяц*: 1 199 ₽ — начни без лишних обязательств\n"
            "🔹 *1 год*: 11 999 ₽ — выгодно, если хочешь постоянную опору\n\n"
            "Выбери вариант подписки ниже:",
            reply_markup=subscription_plan_keyboard(),
            parse_mode="Markdown"
        )
        return

    if text in ["🗓 Купить на 1 месяц", "📅 Купить на 1 год"]:
        plan = "monthly" if text == "🗓 Купить на 1 месяц" else "yearly"
        invoice_id = int(time.time())
        payment_url = generate_payment_url(telegram_id, invoice_id, plan)
        bot.send_message(
            chat_id,
            "🔗 Нажмите кнопку ниже, чтобы перейти к оплате:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Перейти к оплате", url=payment_url)]
            ])
        )
        return

    if text in ["📜 Условия пользования", "❓ Гид по боту"]:
        filename = {
            "❓ Гид по боту": "guide.txt",
            "📜 Условия пользования": "rules.txt"
        }.get(text)
        try:
            with open(f"texts/{filename}", "r", encoding="utf-8") as f:
                response = f.read()
        except FileNotFoundError:
            response = "Файл с информацией пока не загружен."
        bot.send_message(chat_id, response, reply_markup=main_menu())
        return

    if text == "🔄 Сбросить диалог":
        reset_user_thread(db, user)
        bot.send_message(
            chat_id,
            "🔁 Диалог сброшен. Ты можешь начать новый разговор, и я буду воспринимать всё с чистого листа.",
            reply_markup=main_menu()
        )
        return
        
    if text == "🔙 Назад в главное меню":
        bot.send_message(chat_id, "Вы вернулись в главное меню.", reply_markup=main_menu())
        return

    if text in ["👤 Личный кабинет", "👥 Кабинет", "Личный кабинет"]:
        message_text, markup = generate_cabinet_message(user, telegram_id, db)
        bot.send_message(chat_id, message_text, reply_markup=markup)
        return

    if text == "🤝 Партнёрская программа":
        referrals_count = db.query(User).filter(User.referrer_code == telegram_id).count()
        total_earned = user.ref_earned or 0
        balance = user.ref_earned or 0
        message_text = generate_withdraw_info(user, referrals_count, total_earned, balance)
        bot.send_message(chat_id, message_text, reply_markup=main_menu())
        return

    # 🔐 Проверка лимита сообщений
    if not user.is_unlimited and user.free_messages_used >= FREE_MESSAGES_LIMIT:
        bot.send_message(
            chat_id,
            "⚠️ Превышен лимит бесплатных сообщений.\nОформите подписку для продолжения.",
            reply_markup=main_menu()
        )
        return

    # 🧐 Обработка кризисных сообщений
    crisis_level = classify_crisis_level(text)
    if crisis_level in ["high", "medium", "low"]:
        log_crisis_message(telegram_id, text, level=crisis_level)
        if crisis_level == "high":
            bot.send_message(chat_id, (
                "Мне очень жаль, что ты сейчас испытываешь такие тяжёлые чувства.\n\n"
                "Если тебе тяжело и возникают мысли навредить себе — важно не оставаться с этим наедине. "
                "Обратись к специалисту или кризисной службе. 💙\n\n"
                "Я рядом, чтобы поддержать тебя информационно. Ты не один(одна)."
            ))
            return

    # 🤖 GPT-диалог
    try:
        assistant_response, thread_id = send_message_to_assistant(user.thread_id, text)
    except Exception as e:
        print('❌ Ошибка в GPT:', e)
        if "run is active" in str(e):
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
