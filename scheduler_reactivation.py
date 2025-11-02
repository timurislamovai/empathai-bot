# scheduler_reactivation.py
"""
Автоматическая рассылка напоминаний неактивным пользователям (6+ дней).
Запускается ежедневно в 22:00 по времени Asia/Almaty.
Отправка проходит с троттлингом 1 сообщение/сек и подробным отчётом в логах.
"""

import asyncio
import random
from datetime import datetime, timedelta, date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import SessionLocal
from bot_instance import bot
from html import escape

# --- Импорты исключений Telegram (aiogram 3.x) ---
try:
    from aiogram.exceptions import (
        TelegramForbiddenError,
        TelegramBadRequest,
        TelegramRetryAfter,
        TelegramNetworkError,
    )
except Exception:
    # fallback на старые имена (aiogram 2.x)
    from aiogram.utils.exceptions import (
        BotBlocked as TelegramForbiddenError,
        ChatNotFound as TelegramBadRequest,
        RetryAfter as TelegramRetryAfter,
        TelegramAPIError as TelegramNetworkError,
    )

# --- Константы ---
REACTIVATION_MESSAGES = [
    "🌿 Ила скучает по тебе... Иногда простое общение помогает вернуть внутреннее спокойствие. Хочешь поговорить?",
    "💬 Давно не виделись! Ила готова тебя выслушать, если хочешь поделиться тем, что на душе 💚",
    "✨ Сегодня — хороший день, чтобы снова начать диалог с Илой. Она ждёт тебя 🌸",
]
SEND_SLEEP_SECONDS = 1.0  # 1 сообщение/сек — безопасный троттлинг


# --- Получение списка неактивных пользователей ---
def _fetch_inactive_users(cutoff_dt):
    session = SessionLocal()
    try:
        from models import User
        users = session.query(User).all()
        selected = []
        for u in users:
            tg = getattr(u, "telegram_id", None)
            if not tg:
                continue

            # last_message_at / last_message_date
            lmd = getattr(u, "last_message_at", None) or getattr(u, "last_message_date", None)
            lrs = getattr(u, "last_reactivation_sent", None)

            inactive = False
            if lmd is None or lmd < cutoff_dt:
                inactive = True

            can_send = lrs is None or lrs < cutoff_dt

            if inactive and can_send:
                selected.append({"id": u.id, "telegram_id": tg})
        return selected
    finally:
        session.close()


# --- Отметка, что пользователю отправлено сообщение ---
def _mark_reactivation_sent(telegram_id, now_dt):
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


# --- Основная логика рассылки ---
async def send_reactivation_messages():
    start_ts = datetime.utcnow()
    print("⏰ [Reactivation] start:", start_ts.isoformat())

    cutoff = datetime.utcnow() - timedelta(days=6)
    loop = asyncio.get_running_loop()

    try:
        users = await loop.run_in_executor(None, _fetch_inactive_users, cutoff)
    except Exception as e:
        print("❗ Ошибка при получении списка пользователей:", e)
        return

    total = len(users)
    sent = 0
    failed = 0
    blocked = 0

    print(f"🔍 Найдено неактивных пользователей: {total}")

    for u in users:
        tg = u.get("telegram_id")
        try:
            msg = random.choice(REACTIVATION_MESSAGES)
            await bot.send_message(tg, escape(msg))
            now_dt = datetime.utcnow()
            await loop.run_in_executor(None, _mark_reactivation_sent, tg, now_dt)
            sent += 1
            await asyncio.sleep(SEND_SLEEP_SECONDS)

        except TelegramRetryAfter as e:
            wait = getattr(e, "retry_after", 5)
            print(f"⏳ Telegram просит подождать {wait}s (пользователь {tg})")
            await asyncio.sleep(wait)
            failed += 1

        except TelegramForbiddenError:
            print(f"⛔ Пользователь {tg} заблокировал бота.")
            blocked += 1

        except TelegramBadRequest as e:
            print(f"🚫 Ошибка ChatNotFound/BadRequest ({tg}): {e}")
            failed += 1

        except TelegramNetworkError as e:
            print(f"🚫 Сетевая ошибка Telegram API ({tg}): {e}")
            failed += 1

        except Exception as e:
            print(f"⚠️ Неизвестная ошибка ({tg}): {type(e).__name__}: {e}")
            failed += 1

    end_ts = datetime.utcnow()
    print("✅ [Reactivation] done:", end_ts.isoformat())
    print(
        "📊 [Reactivation report]\n"
        f"Всего найдено: {total}\n"
        f"✅ Отправлено: {sent}\n"
        f"🚫 Ошибки: {failed}\n"
        f"⛔ Заблокировали: {blocked}\n"
        f"⏱ Время выполнения: {(end_ts - start_ts).total_seconds():.1f}s"
    )


# --- Запуск планировщика ---
def start_scheduler():
    """Запуск планировщика: каждый день в 22:00 по времени Asia/Almaty"""
    try:
        scheduler = AsyncIOScheduler(timezone="Asia/Almaty")
        scheduler.add_job(send_reactivation_messages, "cron", hour=22, minute=0)
        scheduler.start()
        print("🕒 Reactivation scheduler started: daily at 22:00 Asia/Almaty")
    except Exception as e:
        print("⚠️ Ошибка при запуске планировщика реактивации:", e)
