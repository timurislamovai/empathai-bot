
from aiogram import types, F, Router
from aiogram.filters import Command, CommandStart
from bot_instance import dp, bot
from models import get_user_by_telegram_id, create_user
from ui import main_menu, subscription_plan_keyboard
from database import SessionLocal
from openai_api import reset_user_thread
from referral import generate_cabinet_message
from cloudpayments import generate_payment_link
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
        "👋 Привет, я Ила — твой личный виртуальный психолог, коуч и наставник по саморазвитию.\n\n"
        "Я здесь, чтобы поддержать тебя, помочь разобраться в чувствах и просто быть рядом, когда это особенно нужно.\n\n"
        "🆓 Сейчас тебе доступно 20 бесплатных сообщений — используй их, чтобы почувствовать, как это работает.\n"
        "💳 Когда лимит закончится, ты сможешь оформить подписку и продолжить общение без ограничений.\n\n"
        "📌 Просто напиши, что у тебя на душе — или выбери пункт из меню ниже.\n\n"
        "⏳ Важно: Ила отвечает в течение 4–8 секунд — она обдумывает твой запрос, чтобы дать тёплый и осмысленный отклик. Немного подожди — и она обязательно ответит.",
        reply_markup=main_menu()
    )
