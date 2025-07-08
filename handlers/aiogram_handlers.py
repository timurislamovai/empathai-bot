from aiogram import types, F
from aiogram.filters import Command
from bot_instance import dp, bot
from models import get_user_by_telegram_id, create_user
from ui import main_menu, subscription_plan_keyboard
from database import SessionLocal
from openai_api import reset_user_thread
from referral import generate_cabinet_message
from cloudpayments import generate_payment_link  # ← добавили
import os
from aiogram import Router

router = Router()

# 🚀 Старт и создание пользователя с ref-кодом
@router.message(Command("start"))
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
        "💡 _С Ила AI Бот ты получаешь поддержку каждый день — как от внимательного собеседника._\n\n"
        "🔹 *1 месяц*: 1 199 ₽ — начни без лишних обязательств\n"
        "🔹 *1 год*: 11 999 ₽ — выгодно, если хочешь постоянную опору\n\n"
        "Выбери вариант подписки ниже:",
        reply_markup=subscription_plan_keyboard(),
        parse_mode="Markdown"
    )

# 🔗 Оплата: 1 месяц / 1 год
@router.message(F.text.in_(["🗓 Купить на 1 месяц", "📅 Купить на 1 год"]))
async def show_payment_link(message: types.Message):
    plan = "monthly" if message.text == "🗓 Купить на 1 месяц" else "yearly"
    telegram_id = str(message.from_user.id)
    amount = 119900 if plan == "yearly" else 119900 // 12  # сумма в копейках

    payment_url = generate_payment_link(telegram_id, plan, amount=amount)

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


from aiogram.filters import CommandStart
from database import SessionLocal
from models import get_user_by_telegram_id, create_user
from ui import main_menu

@router.message(CommandStart())
async def handle_start(message: types.Message):
    db = SessionLocal()
    telegram_id = str(message.from_user.id)

    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        # Если есть реф. код в команде
        ref_code = None
        parts = message.text.strip().split(" ", 1)
        if len(parts) > 1 and parts[1].startswith("ref"):
            ref_code = parts[1].replace("ref", "")
            if not ref_code.isdigit():
                ref_code = None

        user = create_user(db, int(telegram_id), referrer_code=ref_code)
        print(f"[👤] Новый пользователь по ссылке ref: {ref_code}")
    else:
        print(f"[ℹ️] Пользователь уже есть: {telegram_id}")

    await message.answer(
        "👋 Добро пожаловать! Я — Ила, твой ИИ-помощник.\n\nЧем могу поддержать тебя сегодня?",
        reply_markup=main_menu()
    )

