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

    # 👥 Партнёрская информация
    message_text += "\n🤝 Партнёрская программа:\n"
    message_text += f"👥 Приглашено: {user.ref_count} чел.\n"
    message_text += f"💸 Заработано: {user.ref_earned}₸\n"
    message_text += f"🔗 Ваша ссылка: https://t.me/IlaAIPsychologistBot?start=ref{user.telegram_id}"

    return message_text, main_menu()

from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def generate_withdraw_info(user, telegram_id, db, bot):
    message = f"💸 Ваш заработок: {user.ref_earned}₸\n"
    message += "🔔 Минимальная сумма для вывода: 500₸\n"

    if user.ref_earned >= 500:
        message += "\n📝 Вы можете отправить запрос на вывод средств."
        buttons = [
            [InlineKeyboardButton("📤 Запросить вывод", callback_data="request_withdraw")],
            [InlineKeyboardButton("🔙 Назад в главное меню", callback_data="back_to_menu")]
        ]
    else:
        buttons = [
            [InlineKeyboardButton("🔙 Назад в главное меню", callback_data="back_to_menu")]
        ]

    markup = InlineKeyboardMarkup(buttons)
    return {"text": message, "reply_markup": markup.to_dict()}
