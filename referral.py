from models import User
from telegram import KeyboardButton, ReplyKeyboardMarkup
from datetime import datetime

def generate_cabinet_message(user, telegram_id, db):
    message_text = f"👤 Ваш Telegram ID: {telegram_id}\n"

    if user.is_unlimited:
        message_text += "✅ У вас безлимитный доступ к боту\n"
    elif user.has_paid and user.subscription_expires_at:
        days_left = (user.subscription_expires_at - datetime.utcnow()).days
        message_text += f"📅 Подписка активна до {user.subscription_expires_at.strftime('%d.%m.%Y')} ({days_left} дней осталось)\n"
    else:
        message_text += f"💬 Сообщений использовано: {user.free_messages_used} из 50\n"
        message_text += "⏳ Пробный период: активен\n"

    return message_text, ReplyKeyboardMarkup([
        [KeyboardButton("🤝 Партнёрская программа")]
    ], resize_keyboard=True)


def generate_withdraw_info(user, telegram_id):
    referrals_info = (
        f"👥 Вы ещё никого не пригласили."
        if user.ref_count == 0 else
        f"👥 Вы пригласили: {user.ref_count} человек(а)"
    )

    message_text = (
        f"🔗 Ваша ссылка: https://t.me/EmpathAIChat_bot?start=ref{telegram_id}\n"
        f"💰 Поделитесь ссылкой — и получайте доход\n"
        f"{referrals_info}\n"
        f"💰 Баланс: {user.ref_earned}₸\n"
        f"📈 Всего заработано: {user.ref_earned}₸\n"
        f"💱 Выплаты возможны в рублях\n\n"

        f"Чтобы вывести средства, напишите администратору empathpay@bk.ru\n"
        f"Пожалуйста, укажите:\n"
        f"• Ваш Telegram ID: {telegram_id}\n"
        f"• Сумму для вывода (не менее 5000)\n"
        f"• Номер карты\n"
        f"• ФИО\n"
        f"• Страну проживания\n\n"
        f"После этого администратор свяжется с вами."
    )

    return message_text, ReplyKeyboardMarkup([
        [KeyboardButton("👤 Личный кабинет")]
    ], resize_keyboard=True)
