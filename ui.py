from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💳 Купить подписку")],
            [KeyboardButton(text="📜 Условия пользования"), KeyboardButton(text="❓ Гид по боту")],
            [KeyboardButton(text="🔄 Сбросить диалог")],
            [KeyboardButton(text="👤 Личный кабинет"), KeyboardButton(text="🤝 Партнёрская программа")]
        ],
        resize_keyboard=True
    )

def subscription_plan_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🗓 Купить на 1 месяц"), KeyboardButton(text="📅 Купить на 1 год")],
            [KeyboardButton(text="🔙 Назад в главное меню")]
        ],
        resize_keyboard=True
    )
