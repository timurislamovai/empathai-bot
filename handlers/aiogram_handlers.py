from aiogram import types
from aiogram.filters import Command
from bot_instance import dp, bot
from models import get_user_by_telegram_id, create_user
from ui import main_menu
from database import SessionLocal

@dp.message(Command("start"))
async def handle_start(message: types.Message):
    chat_id = message.chat.id
    telegram_id = str(message.from_user.id)
    text = message.text

    db = SessionLocal()
    user = get_user_by_telegram_id(db, telegram_id)

    # Извлекаем реф-код
    ref_code = None
    parts = text.strip().split(" ", 1)
    if len(parts) > 1:
        ref_code = parts[1].strip()
        if ref_code.startswith("ref"):
            ref_code = ref_code.replace("ref", "", 1)
        if not ref_code.isdigit():
            ref_code = None

    # Создаём пользователя или обновляем
    if not user:
        user = create_user(db, telegram_id, referrer_code=ref_code)
        print(f"[👤] Новый пользователь создан по реф. коду: {ref_code}")
    elif not user.referrer_code and ref_code:
        user.referrer_code = ref_code
        db.commit()
        print(f"[🔁] Реф. код добавлен к существующему пользователю: {ref_code}")

    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Привет, я Ила — твой личный виртуальный психолог и наставник по саморазвитию.\n\n"
        "🆓 Вам доступно 50 бесплатных сообщений.\n"
        "💳 После окончания лимита можно оформить подписку.\n\n"
        "📋 Выберите пункт меню или напишите свой вопрос.",
        reply_markup=main_menu()
    )
