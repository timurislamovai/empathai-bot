"""
scheduler_affirmations.py

Ежедневная рассылка аффирмаций всем пользователям в 09:00 Asia/Almaty.
Отправка 1 сообщения в секунду, чтобы не перегружать Telegram API.
Ведётся краткий отчёт в логах: всего / получили / ошибки / заблокировали.
"""

import asyncio
import random
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import SessionLocal
from bot_instance import bot

from html import escape
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramRetryAfter, TelegramNetworkError


AFFIRMATIONS_FILE = "affirmations.txt"
SEND_SLEEP_SECONDS = 1.0  # 1 сообщение в секунду — безопасно

def _fetch_all_user_ids():
    """Берём всех пользователей из базы и возвращаем список их telegram_id."""
    session = SessionLocal()
    try:
        from models import User
        users = session.query(User).all()
        ids = []
        for u in users:
            if getattr(u, "telegram_id", None):
                ids.append(u.telegram_id)
        return ids
    finally:
        session.close()


async def send_affirmations():
    """Основная функция рассылки"""
    start_ts = datetime.utcnow()
    print("⏰ [Affirmations] start:", start_ts.isoformat())

    # Читаем все аффирмации из файла
    try:
        with open(AFFIRMATIONS_FILE, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print("❗ Не удалось прочитать affirmations.txt:", e)
        return

    if not lines:
        print("❗ Файл affirmations.txt пуст — рассылка пропущена.")
        return

    loop = asyncio.get_running_loop()
    try:
        user_ids = await loop.run_in_executor(None, _fetch_all_user_ids)
    except Exception as e:
        print("❗ Ошибка получения пользователей из БД:", e)
        return

    total_users = len(user_ids)
    sent_count = 0
    failed_count = 0
    blocked_count = 0

    print(f"🔍 Найдено пользователей для рассылки: {total_users}")

    # Клавиатура с callback (будет одинаковая для всех пользователей)
    kb = InlineKeyboardMarkup(inline_keyboard=[], row_width=1)
    kb.add(InlineKeyboardButton("💬 Поговорить с Илой", callback_data="start_chat_from_affirmation"))

    for tg_id in user_ids:
        try:
            raw = random.choice(lines)
            safe = escape(raw)
            formatted = (
                "🌞 <b>Аффирмация дня от Илы</b> 🌿\n\n"
                f"<i>{safe}</i>\n\n"
                "Если хочешь обсудить это — нажми кнопку ниже и начни диалог."
            )
    
            await bot.send_message(
                tg_id,
                formatted,
                parse_mode="HTML",
                reply_markup=kb
            )
            sent_count += 1
            await asyncio.sleep(SEND_SLEEP_SECONDS)
    
        except TelegramRetryAfter as e:
            wait = getattr(e, "retry_after", 5)
            print(f"⏳ Telegram просит подождать {wait} секунд.")
            await asyncio.sleep(wait)
            failed_count += 1
    
        except TelegramForbiddenError:
            print(f"⛔ Пользователь {tg_id} заблокировал бота.")
            blocked_count += 1
    
        except TelegramBadRequest as e:
            print(f"🚫 Ошибка: чат не найден или некорректный запрос ({tg_id}): {e}")
            failed_count += 1
    
        except TelegramNetworkError as e:
            print(f"🚫 Сетевая ошибка Telegram API ({tg_id}): {e}")
            failed_count += 1
    
        except Exception as e:
            print(f"⚠️ Неизвестная ошибка при отправке {tg_id}: {type(e).__name__}: {e}")
            failed_count += 1

    end_ts = datetime.utcnow()
    print("✅ [Affirmations] done:", end_ts.isoformat())
    print(
        "📊 [Affirmations report]\n"
        f"Всего пользователей: {total_users}\n"
        f"✅ Получили сообщение: {sent_count}\n"
        f"🚫 Не получили (ошибка): {failed_count}\n"
        f"⛔ Заблокировали бота: {blocked_count}\n"
        f"⏱ Время выполнения: {(end_ts - start_ts).total_seconds():.1f}s"
    )


def start_scheduler():
    """Запускает ежедневную рассылку аффирмаций (09:00 по Алматы)"""
    scheduler = AsyncIOScheduler(timezone="Asia/Almaty")
    scheduler.add_job(send_affirmations, "cron", hour=12, minute=26)
    scheduler.start()
    print("🕒 Affirmations scheduler started: daily at 09:00 Asia/Almaty")
