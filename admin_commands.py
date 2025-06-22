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

        # Добавля
