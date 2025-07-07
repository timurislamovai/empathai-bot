# handlers/aiogram_handlers.py

from aiogram import types
from bot_instance import dp, bot
from ui import main_menu  # используем твою клавиатуру

@dp.message(lambda message: message.text == "/start")
async def start_command(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать! Я Ила, ваш ИИ-психолог. Чем могу помочь?",
        reply_markup=main_menu()
    )

@dp.message()
async def handle_text_message(message: types.Message):
    text = message.text

    if text == "👤 Личный кабинет":
        await message.answer("🔐 Ваш кабинет скоро будет доступен.")
    elif text == "💳 Купить подписку":
        await message.answer("💳 Система оплаты пока настраивается.")
    elif text == "🔄 Сбросить диалог":
        await message.answer("♻️ Диалог сброшен.")
    else:
        await message.answer("🤖 Пока я не понимаю это сообщение.")

