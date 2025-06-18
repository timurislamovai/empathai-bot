# admin_commands.py

from sqlalchemy.orm import Session
from sqlalchemy import func
from telegram import Bot

from models import User


def handle_admin_stats(db: Session, chat_id: int, bot: Bot):
    # Получаем топ 10 пользователей по количеству приглашённых
    top_referrers = (
        db.query(User.referrer_code, func.count(User.id).label("ref_count"))
        .filter(User.referrer_code.isnot(None))
        .group_by(User.referrer_code)
        .order_by(func.count(User.id).desc())
        .limit(10)
        .all()
    )

    total_invited = db.query(User).filter(User.referrer_code.isnot(None)).count()
    unique_referrers = db.query(User.referrer_code).filter(User.referrer_code.isnot(None)).distinct().count()

    # Формируем текст
    if not top_referrers:
        stats_text = "📊 Пока никто никого не пригласил."
    else:
        stats_text = "📊 Реферальная статистика (ТОП 10):\n"
        for i, (ref_code, count) in enumerate(top_referrers, start=1):
            stats_text += f"{i}. {ref_code} — {count} приглашённых\n"

        stats_text += f"\n🔢 Пользователей с рефералами: {unique_referrers}"
        stats_text += f"\n📈 Всего приглашений: {total_invited}"

    bot.send_message(chat_id, stats_text)
