# scheduler_reactivation.py
"""
Устойчивый планировщик рассылки реактивации (6+ дней).
Запускается ежедневно в 22:00 Asia/Almaty.
"""

import asyncio
import random
import traceback
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import SessionLocal, engine
from bot_instance import bot

# импорт клавиатуры тем
from handlers.start_handlers import topics_keyboard

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
    (
        "🌿 Привет, {name}!\n\n"
        "Это Ила. Я заметила, что тебя не было какое-то время.\n"
        "Иногда важно просто снова сделать паузу — вдох, выдох, чуть спокойствия.\n\n"
        "💬 Хочешь немного поддержки? Выбери, с чего начнём:"
    ),
    (
        "🌸 Привет, {name}!\n\n"
        "Давно не общались — надеюсь, у тебя всё спокойно.\n"
        "Если чувствуешь, что немного устал(а), я рядом 🌿\n\n"
        "Хочешь немного поддержки? Выбери, с чего начнём:"
    ),
]

SEND_SLEEP_SECONDS = 1.0  # 1 сообщение/сек — безопасный троттлинг

# --- Вспомогательные функции ---

def _fetch_inactive_users(cutoff_dt):
    """
    Возвращает список словарей: {id, telegram_id, first_name}
    Защищено от ошибок схемы: если прямой селект столбцов падает, пытаем получить
    список через ORM и getattr на каждый объект.
    """
    session = SessionLocal()
    try:
        # Попробуем сначала безопасно запросить только нужные колонки (если они есть)
        try:
            # select specific columns reduces chance of attribute access errors
            rows = session.query(
                # SQLAlchemy will throw if column doesn't exist, so wrap in try
                ).all()  # intentionally empty — we'll try alternate approach below
        except Exception:
            # fallback: выбрать все и делать getattr (устойчивее к изменениям)
            pass

        users = []
        # делаем ORM-выборку по кускам, чтобы не держать большие объёмы памяти
        try:
            from models import User
            all_users = session.query(User).yield_per(200).all()
        except Exception as e:
            # если чтение всех объектов конструкцией .all() упало — логируем и пробуем raw SQL
            print("❗ Ошибка при ORM-выборке пользователей:", e)
            traceback.print_exc()
            try:
                # fallback raw SQL: минимальный запрос для безопасности
                res = session.execute("SELECT id, telegram_id, first_name, last_message_at, last_message_date, last_reactivation_sent FROM users")
                for row in res:
                    uid, tg, fname, lma, lmd, lrs = row
                    users.append({"id": uid, "telegram_id": tg, "first_name": fname, "last_message": lma or lmd, "last_reactivation_sent": lrs})
                return users
            except Exception as e2:
                print("❗ Ошибка при raw SQL SELECT users:", e2)
                traceback.print_exc()
                return []

        # теперь фильтруем уже на python-уровне
        for u in all_users:
            try:
                tg = getattr(u, "telegram_id", None)
                if not tg:
                    continue

                # Берём последнее взаимодействие — сначала last_message_at, затем last_message_date
                lmd = getattr(u, "last_message_at", None) or getattr(u, "last_message_date", None)
                lrs = getattr(u, "last_reactivation_sent", None)

                # Считаем неактивным если нет ласт-мержа или он раньше cutoff
                inactive = lmd is None or (isinstance(lmd, datetime) and lmd < cutoff_dt) or (not isinstance(lmd, datetime) and lmd and datetime.combine(lmd, datetime.min.time()) < cutoff_dt)
                can_send = lrs is None or (isinstance(lrs, datetime) and lrs < cutoff_dt)

                if inactive and can_send:
                    users.append({
                        "id": getattr(u, "id", None),
                        "telegram_id": tg,
                        "first_name": getattr(u, "first_name", None),
                    })
            except Exception as e:
                # Пропускаем проблемного пользователя, но логируем
                print(f"⚠️ Проблема при обработке пользователя (id:{getattr(u,'id', None)}): {e}")
                traceback.print_exc()
                continue

        return users

    finally:
        session.close()


def _mark_reactivation_sent(telegram_id, now_dt):
    session = SessionLocal()
    try:
        from models import User
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            # пытаемся установить поле; если его нет — игнорируем
            try:
                user.last_reactivation_sent = now_dt
                session.add(user)
                session.commit()
            except Exception as e:
                print(f"⚠️ Не удалось пометить last_reactivation_sent для {telegram_id}: {e}")
                traceback.print_exc()
                session.rollback()
    finally:
        session.close()


# --- Основная логика рассылки ---
async def send_reactivation_messages():
    start_ts = datetime.utcnow()
    print("⏰ [Reactivation] start:", start_ts.isoformat())

    cutoff = datetime.utcnow() - timedelta(days=7)
    loop = asyncio.get_running_loop()

    # получаем пользователей безопасно (в sync режиме внутри run_in_executor)
    try:
        users = await loop.run_in_executor(None, _fetch_inactive_users, cutoff)
    except Exception as e:
        print("❗ Ошибка при получении списка пользователей (run_in_executor):", type(e).__name__, e)
        traceback.print_exc()
        return

    total = len(users)
    sent = 0
    failed = 0
    blocked = 0

    print(f"🔍 Найдено неактивных пользователей: {total}")

    for u in users:
        tg = u.get("telegram_id")
        name = u.get("first_name") or "друг"
        try:
            msg_template = random.choice(REACTIVATION_MESSAGES)
            msg = msg_template.format(name=name)

            print(f"✉️ [Reactivation] Отправка пользователю (tg masked) ...")  # не пишем id
            await bot.send_message(tg, msg, reply_markup=topics_keyboard())

            # Помечаем как отправленное в отдельном потоке
            now_dt = datetime.utcnow()
            try:
                await loop.run_in_executor(None, _mark_reactivation_sent, tg, now_dt)
            except Exception as e:
                print(f"⚠️ Не удалось пометить отправку для {tg}: {e}")
                traceback.print_exc()

            sent += 1
            await asyncio.sleep(SEND_SLEEP_SECONDS)

        except TelegramRetryAfter as e:
            wait = getattr(e, "retry_after", 5)
            print(f"⏳ Telegram просит подождать {wait}s (backoff)")
            await asyncio.sleep(wait)
            failed += 1

        except TelegramForbiddenError:
            print(f"⛔ Пользователь заблокировал бота.")
            blocked += 1

        except TelegramBadRequest as e:
            print(f"🚫 Ошибка ChatNotFound/BadRequest: {e}")
            failed += 1

        except TelegramNetworkError as e:
            print(f"🚫 Сетевая ошибка Telegram API: {e}")
            failed += 1

        except Exception as e:
            print(f"⚠️ Неизвестная ошибка при отправке: {type(e).__name__}: {e}")
            traceback.print_exc()
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
    """
    Запуск планировщика реактивации раз в 3 дня (22:00 по времени Asia/Almaty).
    Отправляет только тем, кто не писал ≥7 дней и не получал реактивацию последние 3 дня.
    """
    try:
        scheduler = AsyncIOScheduler(timezone="Asia/Almaty")

        # Запуск каждый 3-й день в 22:00
        scheduler.add_job(
            send_reactivation_messages,
            "cron",
            hour=22,
            minute=0,
            day="*/3",  # каждые 3 дня
        )

        scheduler.start()
        print("🕒 Reactivation scheduler started: every 3 days at 22:00 Asia/Almaty")

    except Exception as e:
        print("⚠️ Ошибка при запуске планировщика реактивации:", e)
        traceback.print_exc()

