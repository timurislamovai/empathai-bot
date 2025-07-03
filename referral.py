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


def generate_withdraw_info(user):
    return (
        f"🔗 <b>Ваша реферальная ссылка:</b>\n"
        f"https://t.me/EmpathAIChat_bot?start=ref{user.telegram_id}\n\n"
        f"🤝 <b>Приглашайте — и зарабатывайте!</b>\n"
        f"💸 Вы получаете <b>30% от каждой оплаченной подписки</b> по вашей ссылке.\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"👥 Приглашено: пока никого\n"
        f"💰 Баланс: 0 ₽\n"
        f"📈 Всего заработано: 0 ₽\n"
        f"💳 Выплаты доступны в рублях\n"
        f"📉 <b>Минимальная сумма вывода: 5 000 ₽</b>\n\n"
        f"🧾 <b>Как получить выплату?</b>\n"
        f"Напишите администратору: <b>empathpay@bk.ru</b>\n"
        f"Укажите:\n"
        f"• Ваш Telegram ID: {user.telegram_id}\n"
        f"• Сумму вывода (от 5 000 ₽)\n"
        f"• Номер банковской карты\n"
        f"• ФИО получателя\n"
        f"• Страну проживания\n\n"
        f"👤 После этого администратор свяжется с вами для подтверждения и перевода."
    )

    return message_text, ReplyKeyboardMarkup([
        [KeyboardButton("👤 Личный кабинет")]
    ], resize_keyboard=True)
