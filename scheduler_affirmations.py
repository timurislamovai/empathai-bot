"""
scheduler_affirmations.py

Ежедневная рассылка аффирмаций всем пользователям в 09:00 Asia/Almaty.
Отправка 1 сообщения в секунду, чтобы не перегружать Telegram API.
"""

import asyncio
import random
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import SessionLocal
from bot_instance import bot

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
    print("⏰ [Affirmations] start:", datetime.utcnow().isoformat())

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

    print(f"🔍 Найдено пользователей для рассылки: {len(user_ids)}")

    for tg_id in user_ids:
        try:
            text = random.choice(lines)
            await bot.send_message(tg_id, text)
            await asyncio.sleep(SEND_SLEEP_SECONDS)
        except Exception as e:
            print(f"⚠️ Ошибка при отправке пользователю {tg_id}: {e}")

    print("✅ [Affirmations] done:", datetime.utcnow().isoformat())


def start_scheduler():
    """Запускает ежедневную рассылку аффирмаций (09:00 по Алматы)"""
    scheduler = AsyncIOScheduler(timezone="Asia/Almaty")
    scheduler.add_job(send_affirmations, "cron", hour=9, minute=0)
    scheduler.start()
    print("🕒 Affirmations scheduler started: daily at 09:00 Asia/Almaty")
