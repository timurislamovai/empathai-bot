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

    text = message.text or ""

    # 🔐 Проверка лимитов (срок подписки / количество бесплатных сообщений)
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

    # ⚠️ Кризисные слова — оставляем обработку в любом случае
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

    # === НОВАЯ ПРОВЕРКА: длина сообщения для бесплатного тарифа ===
    # Проверяем после кризисного анализа, чтобы важные сигналы не терялись
    if not user.is_unlimited and not user.has_paid and len(text) > 400:
        await message.answer(
            "В бесплатном тарифе можно отправлять до 400 символов. Оформите подписку, чтобы писать более длинные сообщения.",
            reply_markup=main_menu()
        )
        return
    # =============================================================

    # 🤖 Отправка в OpenAI
    try:
        assistant_response, thread_id = send_message_to_assistant(
            user.thread_id,
            text,
            is_paid=user.has_paid,
            is_unlimited=user.is_unlimited
        )

    except Exception as e:
        print("❌ Ошибка в GPT:", e)
        if "run is active" in str(e):
            user.thread_id = None
            db.commit()
            assistant_response, thread_id = send_message_to_assistant(
                None,
                text,
                is_paid=user.has_paid,
                is_unlimited=user.is_unlimited
            )
        else:
            await message.answer("⚠️ Произошла ошибка. Попробуй ещё раз позже.")
            return


    if not user.thread_id:
        update_user_thread_id(db, user, thread_id)

    increment_message_count(db, user)

    assistant_response = clean_markdown(assistant_response)

    try:
        await message.answer(assistant_response, reply_markup=main_menu())
    except aiogram.exceptions.TelegramForbiddenError:
        print(f"⚠️ Пользователь {telegram_id} заблокировал бота — сообщение не доставлено.")
    except aiogram.exceptions.TelegramBadRequest as e:
        # Например, если текст слишком длинный или содержит недопустимые символы
        print(f"⚠️ TelegramBadRequest при ответе пользователю {telegram_id}: {e}")
    except Exception as e:
        print(f"⚠️ Не удалось отправить сообщение пользователю {telegram_id}: {e}")


