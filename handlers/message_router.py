from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.orm import Session
from models import User, increment_message_count, get_user_by_telegram_id
from referral import generate_cabinet_message, generate_withdraw_info
from admin_commands import handle_admin_stats
from robokassa import generate_payment_url
from openai_api import reset_user_thread
from ui import main_menu, subscription_plan_keyboard

import time
from datetime import datetime

ADMIN_IDS = ["944583273", "396497806"]  # 🔁 Укажи своих админов

def handle_command(text: str, user: User, chat_id: int, bot: Bot, db: Session):
    if text == "/admin_referrals":
        if str(user.telegram_id) not in ADMIN_IDS:
            bot.send_message(chat_id, "⛔ У вас нет доступа к этой команде.")
            return
        try:
            handle_admin_stats(db, chat_id, bot)
        except Exception as e:
            print(f"❌ Ошибка в handle_admin_stats: {e}")
            bot.send_message(chat_id, f"❌ Ошибка: {e}")
        return

    if text == "/admin_stats":
        if str(user.telegram_id) not in ADMIN_IDS:
            bot.send_message(chat_id, "⛔ У вас нет доступа к этой команде.")
            return
        try:
            total_users = db.query(User).count()
            paid_users = db.query(User).filter(User.has_paid == True).count()
            unlimited_users = db.query(User).filter(User.is_unlimited == True).count()

            bot.send_message(
                chat_id,
                f"📊 Общая статистика:"
                f"👥 Всего пользователей: {total_users}"
                f"💳 С подпиской: {paid_users}"
                f"♾ Безлимит: {unlimited_users}"
            )
        except Exception as e:
            print(f"❌ Ошибка в /admin_stats: {e}")
            bot.send_message(chat_id, f"❌ Ошибка: {e}")
        return

def handle_menu_button(text: str, user: User, chat_id: int, bot: Bot, db: Session):
    if text == "💳 Купить подписку":
        bot.send_message(
            chat_id,
            "💡 _С EmpathAI ты получаешь поддержку каждый день — как от внимательного собеседника._"
            "🔹 *1 месяц*: 1 199 ₽ — начни без лишних обязательств"
            "🔹 *1 год*: 11 999 ₽ — выгодно, если хочешь постоянную опору"
            "Выбери вариант подписки ниже:",
            reply_markup=subscription_plan_keyboard(),
            parse_mode="Markdown"
        )
        return

    if text in ["🗓 Купить на 1 месяц", "📅 Купить на 1 год"]:
        plan = "monthly" if text == "🗓 Купить на 1 месяц" else "yearly"
        invoice_id = int(time.time())
        payment_url = generate_payment_url(user.telegram_id, invoice_id, plan)
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
            response = "⚠️ Файл с информацией пока не загружен."
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

    if text in ["👤 Личный кабинет", "👥 Кабинет", "Личный кабинет"]:
        message_text, markup = generate_cabinet_message(user, str(user.telegram_id), db)
        bot.send_message(chat_id, message_text, reply_markup=markup)
        return

    if text == "🤝 Партнёрская программа":
        referrals_count = db.query(User).filter(User.referrer_code == str(user.telegram_id)).count()
        total_earned = user.ref_earned or 0
        balance = user.ref_earned or 0
        message_text = generate_withdraw_info(user, referrals_count, total_earned, balance)
        bot.send_message(chat_id, message_text, reply_markup=main_menu())
        return

    if text == "🔙 Назад в главное меню":
        bot.send_message(chat_id, "Вы вернулись в главное меню.", reply_markup=main_menu())
        return
