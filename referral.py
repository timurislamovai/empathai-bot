from telegram import KeyboardButton, ReplyKeyboardMarkup
from datetime import datetime, timezone
from models import User

def generate_cabinet_message(user, telegram_id, db):
    total_referrals = db.query(User).filter(User.referrer_code == telegram_id).count()
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    monthly_referrals = db.query(User).filter(
        User.referrer_code == telegram_id,
        User.created_at >= month_start
    ).count()

    if total_referrals > 0:
        referrals_info = f"\n👥 Вы пригласили:\n— Всего: {total_referrals} человек\n— В этом месяце: {monthly_referrals} человек"
    else:
        referrals_info = "\n👥 Вы ещё никого не пригласили."

    message_text = (
        f"👤 Ваш Telegram ID: {telegram_id}\n"
        f"💬 Сообщений использовано: {user.free_messages_used} из 50\n"
        f"⏳ Пробный период: активен\n\n"
        f"🔗 Ваша ссылка: https://t.me/EmpathAI_Bot?start={telegram_id}\n"
        f"💰 Поделитесь ссылкой — и получайте доход"
        f"{referrals_info}\n"
        f"💰 Баланс: {user.balance:.2f}\n"
        f"📈 Всего заработано: {user.total_earned:.2f}\n"
        f"💱 Выплаты возможны в тенге, рублях или долларах"
    )

    markup = ReplyKeyboardMarkup([
        [KeyboardButton("💵 Вывод средств")]
    ], resize_keyboard=True)

    return message_text, markup

def generate_withdraw_info(user, telegram_id):
    message_text = (
        f"👤 Ваш Telegram ID: {telegram_id}\n"
        f"💬 Сообщений использовано: {user.free_messages_used} из 50\n"
        f"Баланс: {user.balance:.2f}\n"
        f"Заработано всего: {user.total_earned:.2f}\n\n"
        f"Чтобы вывести средства, напишите администратору @Timur146\n"
        "Пожалуйста, укажите:\n"
        f"• Ваш Telegram ID: {telegram_id}\n"
        "• Сумму для вывода (не менее 500)\n"
        "• Номер карты\n"
        "• ФИО\n"
        "• Страну проживания\n\n"
        "После этого администратор свяжется с вами."
    )

    return message_text, None  # или main_menu()

