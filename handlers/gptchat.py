from aiogram import types, F, Router
from database import SessionLocal
from datetime import datetime
import os

from models import (
    get_user_by_telegram_id,
    increment_message_count,
    update_user_thread_id,
    create_user  # ← добавь, если не импортировал
)
from openai_api import send_message_to_assistant, reset_user_thread
from utils import clean_markdown
from filters import classify_crisis_level, log_crisis_message
from ui import main_menu

# Инициализация router
router = Router()

FREE_MESSAGES_LIMIT = int(os.environ.get("FREE_MESSAGES_LIMIT", 7))
FREE_MESSAGE_CHAR_LIMIT = 200 # Лимит на количество символов в сообщении для бесплатных пользователей

# Обрабатываем только произвольные сообщения, исключая кнопки
@router.message(
    F.text 
    & ~F.text.in_([
        "💳 Купить подписку",
        "🗓 Купить на 1 месяц",
        "📅 Купить на 1 год",
        "👤 Личный кабинет",
        "❓ Гид по боту",
        "📜 Условия пользования",
        "🔄 Сбросить диалог",
        "🤝 Партнёрская программа",
        "🔙 Назад в главное меню"
    ])
    & ~F.text.startswith("/start")
)

async def handle_gpt_message(message: types.Message):
    db = SessionLocal()
    telegram_id = int(message.from_user.id)
    user = get_user_by_telegram_id(db, telegram_id)

    if not user:
        user = create_user(db, int(telegram_id))
        print(f"[👤] Автоматически создан пользователь в GPT: {telegram_id}")

    # ⏰ Обновим дату последней активности
    user.last_message_at = datetime.utcnow()
    db.commit()

    text = message.text

    # 🔐 Проверка лимитов
    if not user.is_unlimited:
        if user.has_paid:
            if user.subscription_expires_at and user.subscription_expires_at < datetime.utcnow():
                user.has_paid = False
                db.commit()
                await message.answer(
                    "📭 Срок вашей подписки истёк. Пожалуйста, оформите новую подписку.",
                    reply_markup=main_menu()
                )
                return
        else:
            if user.free_messages_used >= FREE_MESSAGES_LIMIT:
                await message.answer(
                    "⚠️ Превышен лимит бесплатных сообщений.\nОформите подписку для продолжения.",
                    reply_markup=main_menu()
                )
                return
                
    # 2. Проверка длины сообщения для бесплатного тарифа
    is_paid = is_subscription_active(user) or user.is_unlimited
    if not is_paid and len(text) > FREE_MESSAGE_CHAR_LIMIT:
        await message.answer(
            f"❌ Ваше сообщение слишком длинное. На бесплатном тарифе разрешено до {FREE_MESSAGE_CHAR_LIMIT} символов. Пожалуйста, сократите свой вопрос.",
            reply_markup=main_menu() # <-- Добавлено
        )
        return

    # ⚠️ Кризисные слова
    crisis_level = classify_crisis_level(text)
    if crisis_level in ["high", "medium", "low"]:
        log_crisis_message(telegram_id, text, level=crisis_level)
        if crisis_level == "high":
            await message.answer(
                "Мне очень жаль, что ты сейчас испытываешь такие тяжёлые чувства.\n\n"
                "Если тебе тяжело и возникают мысли навредить себе — пожалуйста, обратись к специалисту или в кризисную службу. 💙\n\n"
                "Я рядом, чтобы поддержать тебя информационно. Ты не один(одна)."
            )
            return
            
    # 🤖 Отправка в OpenAI
    try:
        # Добавляем инструкцию для модели, если пользователь на бесплатном тарифе
        prompt_modifier = ""
        # Проверяем, что это не платный пользователь
        is_paid = is_subscription_active(user) or user.is_unlimited
        if not is_paid:
            prompt_modifier = " Ответь кратко, в пределах 200 символов."

        # Объединяем сообщение пользователя с инструкцией
        full_message = text + prompt_modifier

        assistant_response, thread_id = send_message_to_assistant(user.thread_id, full_message)

    except Exception as e:
        print("❌ Ошибка в GPT:", e)
        if "run is active" in str(e):
            user.thread_id = None
            db.commit()
            assistant_response, thread_id = send_message_to_assistant(None, full_message) # <-- И здесь тоже
        else:
            await message.answer("⚠️ Произошла ошибка. Попробуй ещё раз позже.")
            return

    if not user.thread_id:
        update_user_thread_id(db, user, thread_id)

    increment_message_count(db, user)

    assistant_response = clean_markdown(assistant_response)
    await message.answer(assistant_response, reply_markup=main_menu())
