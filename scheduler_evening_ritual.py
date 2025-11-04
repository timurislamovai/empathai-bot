# scheduler_evening_ritual.py
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from database import SessionLocal
from models import User
from bot_instance import bot

TIMEZONE = "Asia/Almaty"


async def send_evening_ritual_invite(bot: Bot, user_id: int):
    """
    Отправляет пользователю первое сообщение вечернего ритуала.
    """
    try:
        text = (
            "🌙 *День подходит к концу...*\n\n"
            "Ты прожил(а) ещё один день — со своими мыслями, чувствами, моментами.\n"
            "Хочешь подвести маленький итог вместе со мной? 💫"
        )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✨ Завершить день", callback_data="finish_day")]
        ])

        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        print(f"🌙 Отправлено приглашение к ритуалу пользователю {user_id}")

    except Exception as e:
        print(f"⚠️ Ошибка при отправке вечернего ритуала пользователю {user_id}: {e}")


async def send_evening_ritual_messages():
    """
    Основная функция рассылки вечернего ритуала.
    """
    db = SessionLocal()
    try:
        users = db.query(User).filter(
            (User.has_paid == True) | (User.is_unlimited == True)
        ).all()

        print(f"🕯 Найдено {len(users)} пользователей для вечернего ритуала")

        for user in users:
            await send_evening_ritual_invite(bot, user.telegram_id)
            await asyncio.sleep(0.3)  # чтобы не перегружать Telegram API

    except Exception as e:
        print(f"❌ Ошибка при выполнении вечернего ритуала: {e}")
    finally:
        db.close()


def start_scheduler():
    """
    Запускает планировщик вечернего ритуала.
    """
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(send_evening_ritual_messages, "cron", hour=22, minute=22)
    scheduler.start()
    print("🕒 Evening ritual scheduler started: daily at 22:22 Asia/Almaty")
