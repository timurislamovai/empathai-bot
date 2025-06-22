# admin_commands.py

from sqlalchemy.orm import Session
from sqlalchemy import func
from telegram import Bot

from models import User

# 📊 Обработчик команды /admin_referrals
# Показывает ТОП 10 пользователей, которые пригласили больше всего людей по своей реферальной ссылке
# Также выводит общее количество приглашений и количество уникальных пригласивших
def handle_admin_stats(db: Session, chat_id: int, bot: Bot):
    # Получаем топ 10 пользователей по количеству рефералов (их telegram_id)
    top_referrers = (
        db.query(User.referrer_code, func.count(User.id).label("ref_count"))
        .filter(User.referrer_code.isnot(None))
        .group_by(User.referrer_code)
        .order_by(func.count(User.id).desc())
        .limit(10)
        .all()
    )

    # Подсчитываем общее количество приглашённых пользователей
    total_invited = db.query(User).filter(User.referrer_code.isnot(None)).count()

    # Подсчитываем количество уникальных пользователей, которые кого-то пригласили
    unique_referrers = db.query(User.referrer_code).filter(User.referrer_code.isnot(None)).distinct().count()

    # Формируем текст для отправки
    if not top_referrers:
        stats_text = "📊 Пока никто никого не пригласил."
    else:
        stats_text = "📊 Реферальная статистика (ТОП 10):\n"
        for i, (ref_code, count) in enumerate(top_referrers, start=1):
            stats_text += f"{i}. {ref_code} — {count} приглашённых\n"

        # Добавляем общие цифры
        stats_text += f"\n🔢 Пользователей с рефералами: {unique_referrers}"
        stats_text += f"\n📈 Всего приглашений: {total_invited}"

    # Отправляем сообщение администратору
    bot.send_message(chat_id, stats_text)

from database import SessionLocal
from models import get_user_by_telegram_id
from telegram import Update
from telegram.ext import ContextTypes
from telegram.ext import CommandHandler

# ✅ Команда для админа: выдача безлимита пользователю по Telegram ID
async def give_unlimited(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)

    if telegram_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("⚠️ Использование: /give_unlimited <telegram_id>")
        return

    target_id = context.args[0]
    db = SessionLocal()

    try:
        user = get_user_by_telegram_id(db, target_id)
        if user:
            user.is_unlimited = True
            db.commit()
            await update.message.reply_text(f"✅ Пользователю {target_id} выдан безлимит.")
        else:
            await update.message.reply_text("❌ Пользователь не найден.")
    except Exception as e:
        print("❌ Ошибка в /give_unlimited:", e)
        await update.message.reply_text("❌ Ошибка при выполнении.")
    finally:
        db.close()
