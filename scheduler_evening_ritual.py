import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from bot_instance import bot
from database import SessionLocal
from models import User
from zoneinfo import ZoneInfo
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError

ASIA_ALMATY = ZoneInfo("Asia/Almaty")

# 🌙 Основная функция рассылки вечернего ритуала
async def send_evening_ritual():
    db = SessionLocal()
    try:
        # 💡 Берём только активных пользователей (писали за последние 5 дней)
        cutoff_date = datetime.utcnow() - timedelta(days=5)
        users = db.query(User).filter(User.last_message_date >= cutoff_date).all()
        total_users = len(users)

        print(f"🌙 Запуск вечернего ритуала — активных пользователей: {total_users}")

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✨ Завершить день", callback_data="finish_day")]
        ])

        sent_count = 0
        blocked_count = 0
        failed_count = 0

        for user in users:
            try:
                await bot.send_message(
                    chat_id=int(user.telegram_id),
                    text=(
                        "🌙 *День подходит к концу...*\n\n"
                        "Ты прожил(а) ещё один день — со своими мыслями, чувствами, моментами.\n"
                        "Хочешь подвести маленький итог вместе со мной? 💫"
                    ),
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                sent_count += 1
                await asyncio.sleep(0.3)

            except TelegramForbiddenError:
                blocked_count += 1
                print("🚫 Пользователь заблокировал бота.")

            except Exception as e:
                failed_count += 1
                print(f"⚠️ Ошибка при отправке сообщения: {e}")

        # 📊 Итоговый отчёт
        print("\n===== 🌙 ВЕЧЕРНИЙ РИТУАЛ — ОТЧЁТ =====")
        print(f"👥 Активных пользователей (5 дней): {total_users}")
        print(f"✅ Успешно отправлено: {sent_count}")
        print(f"🚫 Заблокировали бота: {blocked_count}")
        print(f"⚠️ Ошибок при отправке: {failed_count}")
        print("🌘 Рассылка вечернего ритуала завершена.\n")

    finally:
        db.close()


# 🌘 Планировщик
def start_scheduler():
    scheduler = BackgroundScheduler(timezone=ASIA_ALMATY)
    loop = asyncio.get_event_loop()

    async def task_wrapper():
        await send_evening_ritual()

    def run_async():
        asyncio.run_coroutine_threadsafe(task_wrapper(), loop)

    # 🕒 Запуск каждый день в 23:00 Asia/Almaty
    scheduler.add_job(run_async, "cron", hour=23, minute=0)
    scheduler.start()
    print("✅ Evening ritual scheduler запущен (23:00 Asia/Almaty)")
