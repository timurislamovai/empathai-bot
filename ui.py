from telegram import ReplyKeyboardMarkup, KeyboardButton

def subscription_plan_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🗓 Купить на 1 месяц"), KeyboardButton("📅 Купить на 1 год")],
            [KeyboardButton("🔙 Назад в главное меню")]
        ],
        resize_keyboard=True
    )
