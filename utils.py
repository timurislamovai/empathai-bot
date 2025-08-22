import re
from datetime import datetime, timedelta
from sqlalchemy import func
from models import User  # Импорт модели пользователя из базы данных


def clean_markdown(text):
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*]\s+", "• ", text, flags=re.MULTILINE)
    return text


# 📊 Сводка статистики по пользователям и сообщениям
def get_stats_summary(session):
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # 📦 Основная статистика
    total_users = session.query(func.count(User.id)).scalar()
    new_today = session.query(func.count(User.id)).filter(func.date(User.first_seen_at) == now.date()).scalar()
    new_7d = session.query(func.count(User.id)).filter(User.first_seen_at >= week_ago).scalar()
    new_30d = session.query(func.count(User.id)).filter(User.first_seen_at >= month_ago).scalar()

    active_24h = session.query(func.count(User.id)).filter(User.last_message_at >= day_ago).scalar()
    active_7d = session.query(func.count(User.id)).filter(User.last_message_at >= week_ago).scalar()

    inactive = session.query(func.count(User.id)).filter(
        (User.last_message_at == None) | (User.last_message_at < week_ago)
    ).scalar()

    expired_trial = session.query(User).filter(
        User.free_messages_used >= 20,
        User.has_paid == False,
        User.is_unlimited == False
    ).count()

    referred_users = session.query(func.count(User.id)).filter(User.referrer_code != None).scalar()

    # 💳 Подписки
    paid_total = session.query(func.count(User.id)).filter(User.has_paid == True).scalar()
    paid_7d = session.query(func.count(User.id)).filter(User.has_paid == True, User.first_seen_at >= week_ago).scalar()
    paid_30d = session.query(func.count(User.id)).filter(User.has_paid == True, User.first_seen_at >= month_ago).scalar()
    free_total = session.query(func.count(User.id)).filter(User.has_paid == False).scalar()

    # 🔗 Реферальная активность
    referred_total = session.query(func.count(User.id)).filter(User.referrer_code.isnot(None)).scalar()

    # ТОП-15 рефереров
    top_referrals = (
        session.query(
            User.telegram_id,
            User.ref_count,
            User.referral_earned
        )
        .filter(User.ref_count > 0)
        .order_by(User.ref_count.desc())
        .limit(15)
        .all()
    )

    # 📊 Формируем текст
    stats = (
        f"📊 Статистика EmpathAI:\n\n"

        f"👥 Всего пользователей: {total_users}\n"
        f"🆕 Новых сегодня: {new_today}\n"
        f"🆕 За 7 дней: {new_7d}\n"
        f"🆕 За 30 дней: {new_30d}\n\n"

        f"💳 Платных всего: {paid_total}\n"
        f"💳 За 7 дней: {paid_7d}\n"
        f"💳 За 30 дней: {paid_30d}\n\n"

        f"🎁 Бесплатных всего: {free_total}\n"
        f"💤 Неактивных (7+ дней): {inactive}\n"
        f"✅ Активных (за 7 дней): {active_7d}\n\n"

        f"❗ Закончился лимит (20 сообщений): {expired_trial}\n\n"

        f"🔗 Пришли по реф. ссылке: {referred_users}\n"
    )

    if top_referrals:
        stats += "🏆 ТОП-15 рефералов:\n"
        for ref_id, invited, earned in top_referrals:
            earned_rub = round((earned or 0) / 100, 2)
            stats += f"{ref_id} — {invited} чел., {earned_rub:.2f} ₽\n"

    return stats.strip()
