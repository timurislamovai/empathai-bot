from aiogram import types, F
from bot_instance import dp, bot
from utils import clean_markdown
from ui import main_menu, subscription_plan_keyboard
from referral import generate_cabinet_message
from openai_api import send_message_to_assistant, reset_user_thread
from models import get_user_by_telegram_id, update_user_thread_id, increment_message_count
from database import SessionLocal
from filters import classify_crisis_level, log_crisis_message
from datetime import datetime
from cloudpayments import generate_payment_link 
import time
from aiogram import Router
router = Router()


FREE_MESSAGES_LIMIT = 7

@router.message(F.text == "💳 Купить подписку")
async def handle_buy(message: types.Message):
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

@router.message(F.text.in_(["🗓 Купить на 1 месяц", "📅 Купить на 1 год"]))
async def handle_payment_options(message: types.Message):
    telegram_id = str(message.from_user.id)
    plan = "monthly" if "месяц" in message.text else "yearly"
    amount = 10000 if plan == "monthly" else 99000

    link = generate_payment_link(telegram_id, plan=plan)

    await message.answer(
        f"💳 Вот ссылка на оплату подписки:\n\n{link}",
        reply_markup=main_menu()
    )

@router.message(F.text.in_(["📜 Условия пользования", "❓ Гид по боту"]))
async def handle_info_files(message: types.Message):
    filename = {
        "❓ Гид по боту": "guide.txt",
        "📜 Условия пользования": "rules.txt"
    }.get(message.text)
    try:
        with open(f"texts/{filename}", "r", encoding="utf-8") as f:
            response = f.read()
    except FileNotFoundError:
        response = "Файл с информацией пока не загружен."
    await message.answer(response, reply_markup=main_menu())

@router.message(F.text == "🔄 Сбросить диалог")
async def handle_reset(message: types.Message):
    db = SessionLocal()
    telegram_id = str(message.from_user.id)
    user = get_user_by_telegram_id(db, telegram_id)
    reset_user_thread(db, user)
    await message.answer("🔁 Диалог сброшен. Ты можешь начать новый разговор.", reply_markup=main_menu())

@router.message(F.text.in_(["👤 Личный кабинет", "👥 Кабинет", "Личный кабинет"]))
async def handle_cabinet(message: types.Message):
    db = SessionLocal()
    telegram_id = str(message.from_user.id)
    user = get_user_by_telegram_id(db, telegram_id)
    message_text, markup = generate_cabinet_message(user, telegram_id, db)
    await message.answer(message_text, reply_markup=markup)

@router.message(F.text == "🤝 Партнёрская программа")
async def handle_partner(message: types.Message):
    try:
        with open("texts/partner.txt", "r", encoding="utf-8") as file:
            partner_info = file.read()
        await message.answer(partner_info, reply_markup=main_menu())
    except Exception as e:
        print("❌ Ошибка при чтении partner.txt:", e)
        await message.answer("⚠️ Не удалось загрузить информацию о партнёрской программе.", reply_markup=main_menu())

@router.message(F.text == "🔙 Назад в главное меню")
async def handle_back(message: types.Message):
    await message.answer("Вы вернулись в главное меню.", reply_markup=main_menu())
