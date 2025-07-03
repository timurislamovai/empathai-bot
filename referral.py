from models import User
from telegram import KeyboardButton, ReplyKeyboardMarkup
from datetime import datetime
from ui import main_menu  # Подключаем основное меню


def generate_cabinet_message(user, telegram_id, db):
    message_text = f"👤 Ваш Telegram ID: {telegram_id}\n"

    if user.is_unlimited:
        message_text += "✅ У вас безлимитный доступ к боту\n"

    elif user.has_paid and user.subscription_expires_at:
        days_left = (user.subscription_expires_at - datetime.utcnow()).days
        message_text += (
            f"📅 Подписка активна до {user.subscription_expires_at.strftime('%d.%m.%Y')} "
            f"({days_left} дней осталось)\n"
        )

    else:
        message_text += f"💬 Сообщений использовано: {user.free_messages_used} из 50\n"
        message_text += "⏳ Пробный период: активен\n"

    return message_text, main_menu()

    # 👥 Партнёрская информация
    message_text += "\n🤝 Партнёрская программа:\n"
    message_text += f"👥 Приглашено: {user.ref_count} чел.\n"
    message_text += f"💰 Заработано: {user.ref_earned} ₽\n"
    message_text += f"🔗 Ссылка: https://t.me/EmpathAIChat_bot?start={user.telegram_id}\n"

    return message_text, main_menu()


def generate_withdraw_info(user, referrals_count, total_earned, balance):
    return (
        f"🔗 Ваша реферальная ссылка:\n"
        f"https://t.me/EmpathAIChat_bot?start={user.telegram_id}\n"
        f"🤝 Приглашайте — и зарабатывайте!\n"
        f"💸 Вы получаете 30% от каждой оплаченной подписки по вашей ссылке.\n\n"
        f"📊 Статистика:\n"
        f"👥 Приглашено: {referrals_count} чел.\n"
        f"💰 Баланс: {balance} ₽\n"
        f"📈 Всего заработано: {total_earned} ₽\n"
        f"💳 Выплаты доступны в рублях\n"
        f"📉 Минимальная сумма вывода: 5 000 ₽\n\n"
        f"🧾 Как получить выплату?\n"
        f"Напишите администратору: empathpay@bk.ru\n"
        f"Укажите:\n"
        f"• Ваш Telegram ID: {user.telegram_id}\n"
        f"• Сумму вывода (от 5 000 ₽)\n"
        f"• Номер банковской карты\n"
        f"• ФИО получателя\n"
        f"• Страну проживания\n\n"
        f"👤 После этого администратор свяжется с вами для подтверждения и перевода."
    )
