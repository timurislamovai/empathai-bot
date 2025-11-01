# scheduler_reactivation.py
"""
Автопросмотр и рассылка напоминаний неактивным пользователям.
Запускается планировщиком apscheduler каждый день в 22:00 Asia/Almaty.
Отправка проходит с троттлингом 1 сообщение / сек.
"""

import asyncio
import random
from datetime import datetime, timedelta, date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from database import SessionLocal
from bot_instance import bot

# Варианты сообщений — можно поменять/добавить тексты
REACTIVATION_MESSAGES = [
    "🌿 Ила скучает по тебе... Иногда простое общение помогает вернуть внутреннее спокойствие. Хочешь поговорить?",
    "💬 Давно не виделись! Ила готова тебя выслушать, если хочешь поделиться тем, что на душе 💚",
    "✨ Сегодня — хороший день, чтобы снова начать диалог с Ила. Она ждёт тебя 🌸"
]

# Сколько секунд ждать между отправками (троттлинг)
SEND_SLEEP_SECONDS = 1.0  # 1 сообщение в секунду — безопасный минимальный поток

def _fetch_inactive_users(cutoff_date):
    """
    Синхронная функция выполняемая в run_in_executor:
    возвращает список объектов пользователей (id, telegram_id).
    Учитывает:
      - last_message_date < cutoff_date (Date) OR last_message_date is NULL (никогда не писал),
      - last_reactivation_sent is NULL OR last_reactivation_sent < cutoff_date
    """
    session = SessionLocal()
    try:
        from models import User
        # Берём всех пользователей; фильтры выполняем в Python, чтобы корректно работать
        # с Date/DateTime типами, если в схеме есть отличия.
        users = session.query(User).all()
        selected = []
        for u in users:
            # Пропускаем пользователей без telegram_id
            if not getattr(u, "telegram_id", None):
                continue

            # last_message_date может быть Date или None
            lmd = getattr(u, "last_message_date", None)
            # last_reactivation_sent может быть datetime или None
            lrs = getattr(u, "last_reactivation_sent", None)

            # условие: если last_message_date отсутствует -> считаем как неактивный
            inactive = False
            if lmd is None:
                inactive = True
            else:
                # Если lmd это date (без времени), сравниваем с cutoff_date (date)
                if isinstance(lmd, date):
                    if lmd < cutoff_date.date():
                        inactive = True
                else:
                    # если datetime-like
                    try:
                        if lmd < cutoff_date:
                            inactive = True
                    except Exception:
                        # на всякий случай пометим неактивным
                        inactive = True

            # проверяем, не было ли недавно рассылки
            can_send = False
            if lrs is None:
                can_send = True
            else:
                try:
                    if lrs < cutoff_date:
                        can_send = True
                except Exception:
                    can_send = True

            if inactive and can_send:
                selected.append({"id": u.id, "telegram_id": u.telegram_id})
        return selected
    finally:
        session.close()

def _mark_reactivation_sent(telegram_id, now_dt):
    """Отмечаем в БД, что рассылка отправлена пользователю"""
    session = SessionLocal()
    try:
        from models import User
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            user.last_reactivation_sent = now_dt
            session.add(user)
            session.commit()
    finally:
        session.close()

async def send_reactivation_messages():
    """Асинхронная обёртка: получаем список и шлём сообщения через bot"""
    print("⏰ [Reactivation] start:", datetime.utcnow().isoformat())

    cutoff = datetime.utcnow() - timedelta(days=6)  # 6 дней назад (UTC)
    loop = asyncio.get_running_loop()

    # Получаем список пользователей синхронно в thread-pool
    try:
        users = await loop.run_in_executor(None, _fetch_inactive_users, cutoff)
    except Exception as e:
        print("❗ Ошибка выборки пользователей:", e)
        return

    print(f"🔍 Найдено для рассылки: {len(users)} пользователей")

    for u in users:
        tg = u.get("telegram_id")
        try:
            text = random.choice(REACTIVATION_MESSAGES)
            await bot.send_message(tg, text)
            # отмечаем в БД (в пуле потоков)
            now_dt = datetime.utcnow()
            await loop.run_in_executor(None, _mark_reactivation_sent, tg, now_dt)
            await asyncio.sleep(SEND_SLEEP_SECONDS)
        except Exception as e:
            # Частые причины: пользователь заблокировал бота или неверный tg id
            print(f"⚠️ Ошибка отправки {tg}: {e}")

    print("✅ [Reactivation] done:", datetime.utcnow().isoformat())

def start_scheduler():
    """
    Запуск планировщика: каждый день в 22:00 по Asia/Almaty
    """
    scheduler = AsyncIOScheduler(timezone="Asia/Almaty")
    scheduler.add_job(send_reactivation_messages, "cron", hour=22, minute=0)
    scheduler.start()
    print("🕒 Scheduler started: daily at 22:00 Asia/Almaty")
