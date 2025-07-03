from telegram import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("💳 Купить подписку")],
            [KeyboardButton("📜 Условия пользования"), KeyboardButton("❓ Гид по боту")],
            [KeyboardButton("🔄 Сбросить диалог")],
            [KeyboardButton("👤 Личный кабинет"), KeyboardButton("🤝 Партнёрская программа")]
        ],
        resize_keyboard=True
    )
