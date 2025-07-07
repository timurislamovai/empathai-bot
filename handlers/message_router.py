import time
import os

from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.orm import Session

from models import get_user_by_telegram_id, create_user, update_user_thread_id, increment_message_count, User
from database import SessionLocal
from referral import generate_cabinet_message

from admin_commands import handle_admin_stats, handle_admin_referrals, give_unlimited_access

from openai_api import reset_user_thread, send_message_to_assistant
from ui import main_menu, subscription_plan_keyboard
from utils import clean_markdown
from filters import classify_crisis_level, log_crisis_message
from datetime import datetime

ADMIN_IDS = ["944583273", "396497806"]
FREE_MESSAGES_LIMIT = int(os.environ.get("FREE_MESSAGES_LIMIT", 50))

bot = Bot(token=os.environ["TELEGRAM_TOKEN"])


async def handle_update(update, db):
    message = update.get("message")
    print("⚙ handle_update работает, сообщение получено:", message.get("text", ""))
    if not message:
        return

    text = message.get("text", "")
    chat_id = message["chat"]["id"]
    telegram_id = str(message["from"]["id"])

    # ✅ Обработка реферального кода
    ref_code = None
    if text.startswith("/start"):
        parts = text.strip().split(" ", 1)
        ref_code = parts[1].strip() if len(parts) > 1 else None

        if ref_code and ref_code.startswith("ref"):
            ref_code = ref_code.replace("ref", "", 1)
        if ref_code and not ref_code.isdigit():
            ref_code = None

    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        print(f"🆕 Новый пользователь: {telegram_id}")
        user = create_user(db, telegram_id, referrer_code=ref_code)

    if text.startswith("/"):
        handle_command(text, user, chat_id, bot, db)
    else:
        try:
            handle_menu_button(text, user, chat_id, bot, db)
        except Exception as e:
            print(f"❌ Ошибка в handle_menu_button: {e}")
            import traceback
            traceback.print_exc()


async def handle_command(text: str, user: User, chat_id: int, bot: Bot, db: Session):
    if text.startswith("/start"):
        parts = text.strip().split(" ", 1)
        ref_code = parts[1].strip() if len(parts) > 1 else None

        if ref_code and ref_code.startswith("ref"):
            ref_code = ref_code.replace("ref", "", 1)
        if ref_code and not ref_code.isdigit():
            ref_code = None

        if not user:
            user = create_user(db, str(chat_id), referrer_code=ref_code)
            print(f"[👤] Новый пользователь создан по реф. коду: {ref_code}")
        elif not user.referrer_code and ref_code:
            user.referrer_code = ref_code
            db.commit()
            print(f"[🔁] Реф. код добавлен к существующему пользователю: {ref_code}")

        await bot.send_message(
            chat_id,
            "👋 Добро пожаловать!\n\n"
            "Привет, я Ила — твой личный виртуальный психолог и наставник по саморазвитию.\n\n"
            "🆓 Вам доступно 50 бесплатных сообщений.\n"
            "💳 После окончания лимита можно оформить подписку.\n\n"
            "📋 Выберите пункт меню или напишите свой вопрос.",
            reply_markup=main_menu()
        )
        return

    if text == "/admin_stats" and str(user.telegram_id) in ADMIN_IDS:
        handle_admin_stats(db, chat_id, bot)
        return

    if text == "/admin_referrals" and str(user.telegram_id) in ADMIN_IDS:
        handle_admin_referrals(db, chat_id, bot)
        return

    if text.startswith("/give_unlimited") and str(user.telegram_id) in ADMIN_IDS:
        give_unlimited_access(db, bot, chat_id, text)
        return


async def handle_menu_button(text: str, user: User, chat_id: int, bot: Bot, db: Session):
    telegram_id = user.telegram_id

    if text == "💳 Купить подписку":
        await bot.send_message(
            chat_id,
            "💡 _С Ила AI Бот ты получаешь поддержку каждый день — как от внимательного собеседника._\n\n"
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
        await bot.send_message(
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
        await bot.send_message(chat_id, response, reply_markup=main_menu())
        return

    if text == "🔄 Сбросить диалог":
        reset_user_thread(db, user)
        await bot.send_message(
            chat_id,
            "🔁 Диалог сброшен. Ты можешь начать новый разговор, и я буду воспринимать всё с чистого листа.",
            reply_markup=main_menu()
        )
        return

    if text == "🔙 Назад в главное меню":
        await bot.send_message(chat_id, "Вы вернулись в главное меню.", reply_markup=main_menu())
        return

    if text in ["👤 Личный кабинет", "👥 Кабинет", "Личный кабинет"]:
        message_text, markup = generate_cabinet_message(user, telegram_id, db)
        await bot.send_message(chat_id, message_text, reply_markup=markup)
        return

    elif text == "🤝 Партнёрская программа":
        try:
            with open("texts/partner.txt", "r", encoding="utf-8") as file:
                partner_info = file.read()
            await bot.send_message(chat_id, partner_info, reply_markup=main_menu())
        except Exception as e:
            print("❌ Ошибка при чтении partner.txt:", e)
            await bot.send_message(chat_id, "⚠️ Не удалось загрузить информацию о партнёрской программе.", reply_markup=main_menu())
        return



    # Проверка лимита сообщений с учётом подписки
    if not user.is_unlimited:
        if user.has_paid:
            if user.subscription_expires_at and user.subscription_expires_at < datetime.utcnow():
                user.has_paid = False
                db.commit()
                await bot.send_message(
                    chat_id,
                    "📭 Срок вашей подписки истёк. Пожалуйста, оформите новую подписку.",
                    reply_markup=main_menu()
                )
                return
        else:
            if user.free_messages_used >= FREE_MESSAGES_LIMIT:
                await bot.send_message(
                    chat_id,
                    "⚠️ Превышен лимит бесплатных сообщений.\nОформите подписку для продолжения.",
                    reply_markup=main_menu()
                )
                return


    crisis_level = classify_crisis_level(text)
    if crisis_level in ["high", "medium", "low"]:
        log_crisis_message(telegram_id, text, level=crisis_level)
        if crisis_level == "high":
            await bot.send_message(chat_id, (
                "Мне очень жаль, что ты сейчас испытываешь такие тяжёлые чувства.\n\n"
                "Если тебе тяжело и возникают мысли навредить себе — важно не оставаться с этим наедине. "
                "Обратись к специалисту или кризисной службе. 💙\n\n"
                "Я рядом, чтобы поддержать тебя информационно. Ты не один(одна)."
            ))
            return

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
    await bot.send_message(chat_id, assistant_response, reply_markup=main_menu())
