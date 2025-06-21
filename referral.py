
from telegram import KeyboardButton, ReplyKeyboardMarkup
from datetime import datetime, timezone
from models import User

def generate_cabinet_message(user, telegram_id, db):
    message_text = (
        f"👤 Ваш Telegram ID: {telegram_id}\n"
        f"💬 Сообщений использовано: {user.free_messages_used} из 50\n"
        f"⏳ Пробный период: активен"
    )
    return message_text, ReplyKeyboardMarkup([
        [KeyboardButton("🤝 Партнёрская программа")]
    ], resize_keyboard=True)

def generate_withdraw_info(user, telegram_id):
    total_referrals = 0
    from models import User as U
    from database import SessionLocal
    db = SessionLocal()

    try:
        total_referrals = db.query(U).filter(U.referrer_code == telegram_id).count()
    except:
        pass
    finally:
        db.close()

    referrals_info = (
        f"👥 Вы ещё никого не пригласили."
        if total_referrals == 0 else
        f"👥 Вы пригласили: {total_referrals} человек(а)"
    )

    message_text = (
        f"🔗 Ваша ссылка: https://t.me/EmpathAI_Bot?start={telegram_id}\n"
        f"💰 Поделитесь ссылкой — и получайте доход\n"
        f"{referrals_info}\n"
        f"💰 Баланс: {user.balance:.2f}\n"
        f"📈 Всего заработано: {user.total_earned:.2f}\n"
        f"💱 Выплаты возможны в тенге, рублях или долларах\n\n"

        f"Чтобы вывести средства, напишите администратору empathpay@bk.ru\n"
        f"Пожалуйста, укажите:\n"
        f"• Ваш Telegram ID: {telegram_id}\n"
        f"• Сумму для вывода (не менее 500)\n"
        f"• Номер карты\n"
        f"• ФИО\n"
        f"• Страну проживания\n\n"
        f"После этого администратор свяжется с вами."
    )

    return message_text, ReplyKeyboardMarkup([
        [KeyboardButton("👤 Личный кабинет")]
    ], resize_keyboard=True)
