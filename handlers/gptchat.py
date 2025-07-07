from aiogram import types
from bot_instance import dp
from database import SessionLocal
from datetime import datetime
import os

from models import (
    get_user_by_telegram_id,
    increment_message_count,
    update_user_thread_id
)
from openai_api import send_message_to_assistant, reset_user_thread
from utils import clean_markdown
from filters import classify_crisis_level, log_crisis_message
from ui import main_menu

FREE_MESSAGES_LIMIT = int(os.environ.get("FREE_MESSAGES_LIMIT", 50))

@dp.message()
async def handle_gpt_message(message: types.Message):
    db = SessionLocal()
    telegram_id = str(message.from_user.id)
    user = get_user_by_telegram_id(db, telegram_id)
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

    # ⚠️ Кризисные слова
    crisis_level = classify_crisis_level(text)
    if crisis_level in ["high", "medium", "low"]:
        log_crisis_message(telegram_id, text, level=crisis_level)
        if crisis_level == "high":
            await message.answer(
                "Мне очень жаль, что ты сейчас испытываешь такие тяжёлые чувства.\n\n"
                "Если тебе тяжело и возникают мысли навредить
