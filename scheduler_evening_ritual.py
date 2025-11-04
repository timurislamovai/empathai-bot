# scheduler_evening_ritual.py
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, date
from database import SessionLocal
from models import User, EveningRitualLog
from bot_instance import bot
from zoneinfo import ZoneInfo

ASIA_ALMATY = ZoneInfo("Asia/Almaty")

# --- Основная функция рассылки ---
def send_evening_invitation():
    db = SessionLocal()
    try:
        today = date.today()
        users = db.query(User).all()
        count_sent = 0

        for user in users:
            # 💤 Пропускаем неактивных
            if not user.telegram_id:
                continue

            # 🔒 Проверка: был ли уже вечерний ритуал сегодня
            already_done = (
                db.query(EveningRitualLog)
                .filter(EveningRitualLog.user_id == user.id)
                .filter(EveningRitualLog.date == today)
                .count() > 0
            )
            if already_done:
                print(f"⏩ Пропущен {user.telegram_id} — ритуал уже пройден сегодня.")
                continue

            # 🔕 Пропускаем, если пользователь давно неактивен (7+ дней)
            if user.last_message_date and (today - user.last_message_date).days > 7:
                continue

            # 🌙 Текст приглашения
            text = (
                "🌙 *День подходит к концу...*\n\n"
                "Ты прожил(а) ещё один день — со своими мыслями, чувствами, моментами.\n"
                "Хочешь подвести маленький итог вместе со мной? 💫"
            )

            try:
                bot.loop.create_task(bot.send_message(
                    chat_id=int(user.telegram_id),
                    text=text,
                    parse_mode="Markdown",
                    reply_markup={
                        "inline_keyboard": [
                            [{"text": "✨ Завершить день", "callback_data": "finish_day"}]
                        ]
                    }
                ))
                count_sent += 1
            except Exception as e:
                print(f"⚠️ Ошибка при отправке ритуала пользователю {user.telegram_id}: {e}")

        print(f"🌙 Рассылка вечернего ритуала завершена. Отправлено {count_sent} сообщений.")

    except Exception as e:
        print(f"❌ Ошибка в send_evening_invitation: {e}")
    finally:
        db.close()


# --- Планировщик ---
def start_scheduler():
    scheduler = BackgroundScheduler(timezone=ASIA_ALMATY)
    scheduler.add_job(send_evening_invitation, "cron", hour=22, minute=22)
    scheduler.start()
    print("🕒 Evening ritual scheduler started: daily at 22:22 Asia/Almaty")
