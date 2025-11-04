import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from bot_instance import bot
from database import SessionLocal
from models import User
from zoneinfo import ZoneInfo

ASIA_ALMATY = timezone("Asia/Almaty")

# 🌙 Основная функция рассылки
async def send_evening_ritual():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"🌙 Запуск вечернего ритуала — всего пользователей: {len(users)}")

        for user in users:
            try:
                await bot.send_message(
                    chat_id=int(user.telegram_id),
                    text="🌙 *День подходит к концу...*\n\n"
                         "Ты прожил(а) ещё один день — со своими мыслями, чувствами, моментами.\n"
                         "Хочешь подвести маленький итог вместе со мной? 💫",
                    parse_mode="Markdown",
                    reply_markup=None
                )
                await asyncio.sleep(0.3)  # чтобы не попасть под rate-limit
            except Exception as e:
                print(f"⚠️ Ошибка при отправке ритуала пользователю {user.telegram_id}: {e}")

        print("🌙 Рассылка вечернего ритуала завершена.")

    finally:
        db.close()


# 🌘 Планировщик (фиксация loop'а)
def start_scheduler():
    scheduler = BackgroundScheduler(timezone=ASIA_ALMATY)
    loop = asyncio.get_event_loop()

    async def task_wrapper():
        await send_evening_ritual()

    def run_async():
        asyncio.run_coroutine_threadsafe(task_wrapper(), loop)

    scheduler.add_job(run_async, "cron", hour=23, minute=43)
    scheduler.start()
    print("✅ Evening ritual scheduler запущен (22:22 Asia/Almaty)")
