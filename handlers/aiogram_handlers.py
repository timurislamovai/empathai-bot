
from aiogram import types, F, Router
from aiogram.filters import Command, CommandStart
from bot_instance import dp, bot
from models import get_user_by_telegram_id, create_user
from ui import main_menu, subscription_plan_keyboard
from database import SessionLocal
from openai_api import reset_user_thread
from referral import generate_cabinet_message
from cloudpayments import generate_payment_link

from aiogram import types
from bot_instance import dp, bot

import os


router = Router()

# 📂 Личный кабинет
@router.message(F.text == "👤 Личный кабинет")
async def show_cabinet(message: types.Message):
    db = SessionLocal()
    telegram_id = str(message.from_user.id)
    user = get_user_by_telegram_id(db, telegram_id)

    text, markup = generate_cabinet_message(user, telegram_id, db)
    await message.answer(text, reply_markup=markup)

# 💳 Купить подписку
@router.message(F.text == "💳 Купить подписку")
async def show_subscription_options(message: types.Message):
    await message.answer(
        "💡 С Ила AI ты сразу начинаешь с бесплатного тарифа — 7 сообщений до 400 символов. "
        "Ничего подключать не нужно, он активируется автоматически при первом обращении.\n\n"
        "Если хочешь больше — доступны расширенные тарифы:\n\n"
        "🔹 1 месяц — 299 ₽\n"
        "Полный доступ без ограничений: полноценные вопросы, развёрнутые ответы, сохранение истории и персонализация.\n\n"
        "🔹 1 год — 2999 ₽\n"
        "Все преимущества месячного тарифа + стабильность и суперэкономия. "
        "Ты получаешь поддержку на весь год и +2 месяца в подарок ₽.\n\n"
        "Выбери подходящий тариф ниже 👇",
        reply_markup=subscription_plan_keyboard(),
        parse_mode="Markdown"
    )

# 🔗 Оплата: 1 месяц / 1 год
@router.message(F.text.in_(["🗓 Купить на 1 месяц", "📅 Купить на 1 год"]))
async def show_payment_link(message: types.Message):
    plan = "monthly" if message.text == "🗓 Купить на 1 месяц" else "yearly"
    telegram_id = str(message.from_user.id)
    amount = 119900 if plan == "yearly" else 119900 // 12  # сумма в копейках

    payment_url = generate_payment_link(telegram_id, plan)

    await message.answer(
        "🔗 Нажмите кнопку ниже, чтобы перейти к оплате:",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="💳 Перейти к оплате", url=payment_url)]
            ]
        )
    )

# 📜 Условия + ❓ Гид
@router.message(F.text.in_(["📜 Условия пользования", "❓ Гид по боту"]))
async def send_static_text(message: types.Message):
    filename = {
        "❓ Гид по боту": "texts/guide.txt",
        "📜 Условия пользования": "texts/rules.txt"
    }.get(message.text)

    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = "⚠️ Файл пока не загружен."

    await message.answer(content, reply_markup=main_menu())

# 🔄 Сбросить диалог
@router.message(F.text == "🔄 Сбросить диалог")
async def reset_dialog(message: types.Message):
    db = SessionLocal()
    user_id = str(message.from_user.id)
    user = get_user_by_telegram_id(db, user_id)
    reset_user_thread(db, user)

    await message.answer("🔁 Диалог сброшен. Можешь начать новый разговор.", reply_markup=main_menu())

# 🤝 Партнёрская программа
@router.message(F.text == "🤝 Партнёрская программа")
async def send_partner_info(message: types.Message):
    try:
        with open("texts/partner.txt", "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = "⚠️ Информация пока не загружена."

    await message.answer(content, reply_markup=main_menu())

# 🔙 Назад в главное меню
@router.message(F.text == "🔙 Назад в главное меню")
async def back_to_main(message: types.Message):
    await message.answer("📋 Главное меню:", reply_markup=main_menu())

# 🚀 Хендлер /start с реф-кодом
@router.message(CommandStart())
async def handle_start(message: types.Message):
    db = SessionLocal()
    telegram_id = str(message.from_user.id)

    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        # Извлекаем реф. код из /start ref123
        ref_code = None
        parts = message.text.strip().split(" ", 1)
        if len(parts) > 1 and parts[1].startswith("ref"):
            ref_code = parts[1].replace("ref", "")
            if not ref_code.isdigit():
                ref_code = None

        user = create_user(db, int(telegram_id), referrer_code=ref_code)
        print(f"[👤] Новый пользователь создан по ссылке ref: {ref_code}")
    else:
        print(f"[ℹ️] Пользователь уже есть: {telegram_id}")

    await message.answer(
        "👋 Привет, я — Ила. Твоя ИИ-собеседница на каждый день.\n\n"
        "Я здесь, чтобы быть рядом: выслушать, поддержать, помочь разобраться в себе. Даже когда кажется, что «всё нормально» — ты не один.\n\n"
        "🆓 Сейчас тебе доступно 7 бесплатных сообщений. Этого достаточно, чтобы почувствовать: ежедневное общение с Илой — это простая и тёплая забота о себе.\n\n"
        "💳 Хочешь продолжить? Оформи подписку и говори с Илой без ограничений — каждый день, когда захочется.\n\n"
        "📣 Подписывайся на наш канал @IlaAIPsychologist — там полезные материалы, поддержка и напоминания заботиться о себе.\n\n"
        "📌 Просто напиши, что у тебя внутри — или выбери пункт из меню ниже.\n\n"
        "⏳ Ила отвечает в течение 4–8 секунд. Немного подожди — и получишь вдумчивый, человечный отклик.\n\n"
        "🔞 Бот доступен только для пользователей от 18 лет.",
        reply_markup=main_menu()
    )

@dp.callback_query_handler(lambda c: c.data == "start_chat_from_affirmation")
async def start_chat_from_affirmation(callback_query: types.CallbackQuery):
    """Обработка кнопки 'Поговорить с Илой' под аффирмацией"""
    user_id = callback_query.from_user.id

    # Убираем кнопку из исходного сообщения (чтобы не нажимали повторно)
    try:
        await bot.edit_message_reply_markup(
            chat_id=user_id,
            message_id=callback_query.message.message_id,
            reply_markup=None
        )
    except Exception:
        pass  # не критично, если сообщение уже нельзя отредактировать

    # Отправляем приветственное сообщение
    await bot.send_message(
        chat_id=user_id,
        text="🌿 Рада, что ты решил поговорить! Расскажи, что чувствуешь или что волнует тебя сегодня."
    )

    # Telegram ожидает ответ, чтобы убрать "часики" на кнопке
    await callback_query.answer()
