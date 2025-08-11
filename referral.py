from models import User
from datetime import datetime
from ui import main_menu  # Подключаем клавиатуру из aiogram

def generate_cabinet_message(user, telegram_id, db):
    if user is None:
        return "❌ Пользователь не найден. Отправьте любое сообщение боту, чтобы зарегистрироваться.", main_menu()

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
        message_text += f"💬 Сообщений использовано: {user.free_messages_used} из 20\n"
        message_text += "⏳ Пробный период: активен\n"

    # 🤝 Партнёрская информация
    message_text += "\n🤝 Партнёрская программа:\n"
    message_text += f"🔗 Ваша ссылка: https://t.me/EmpathAIChat_bot?start=ref{user.telegram_id}\n"
    message_text += "🤝 Приглашайте — и зарабатывайте!\n"
    message_text += "💸 Вы получаете 30% от каждой оплаченной подписки по вашей ссылке.\n\n"

    # Считаем количество приглашённых пользователей
    invited_count = db.query(User).filter(User.referrer_code == str(user.telegram_id)).count()

    message_text += f"👥 Приглашено: {invited_count} чел.\n"
    earned_rub = round((user.referral_earned or 0.0), 2)
    paid_rub = round((user.referral_paid or 0.0), 2)
    message_text += f"💸 Заработано: {earned_rub} ₽\n"
    message_text += f"💳 Выплачено: {paid_rub} ₽\n"
    message_text += f"💰 Остаток к выплате: {round(earned_rub - paid_rub, 2)} ₽\n\n"

    message_text += "📤 Как получить выплату?\n"
    message_text += "Напишите администратору: empathpay@bk.ru\n"
    message_text += "🔔 Минимальная сумма для вывода: 5000 рублей"

    return message_text, main_menu()
