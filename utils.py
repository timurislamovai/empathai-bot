import re

def clean_markdown(text):
    # Удаление жирного и курсивного
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)

    # Удаление заголовков (##, # и т.д.)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)

    # Удаление цитат ">"
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)

    # Замена маркеров списков (-, *) на •
    text = re.sub(r"^\s*[-*]\s+", "• ", text, flags=re.MULTILINE)

    return text


from datetime import datetime, timedelta
from sqlalchemy import func
from models import User  # Импорт модели пользователя из базы данных

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

    # 💳 Подписки
    paid_total = session.query(func.count(User.id)).filter(User.has_paid == True).scalar()
    paid_7d = session.query(func.count(User.id)).filter(User.has_paid == True, User.first_seen_at >= week_ago).scalar()
    paid_30d = session.query(func.count(User.id)).filter(User.has_paid == True, User.first_seen_at >= month_ago).scalar()
    free_total = session.query(func.count(User.id)).filter(User.has_paid == False).scalar()

    # 📬 Сообщения
    total_messages = session.query(func.sum(User.total_messages)).scalar() or 0
    messages_24h = session.query(func.sum(User.total_messages)).filter(User.last_message_at >= day_ago).scalar() or 0

    # 🔗 Реферальная активность
    referred_total = session.query(func.count(User.id)).filter(User.referrer_code != None).scalar()

    # Получаем список Telegram ID рефереров и количество приглашённых
    top_referrals_raw = (
        session.query(User.referrer_code, func.count(User.id).label("invited"))
        .filter(User.referrer_code != None)
        .group_by(User.referrer_code)
        .order_by(func.count(User.id).desc())
        .limit(15)
        .all()
    )

    # Получаем суммы заработка по реферерам
    ref_codes = [row[0] for row in top_referrals_raw]
    ref_earned_map = dict(
        session.query(User.telegram_id, func.coalesce(User.referral_earned, 0))
        .filter(User.telegram_id.in_(ref_codes))
        .all()
    )

    # Сбор финального списка
    top_referrals = []
    for ref_code, invited in top_referrals_raw:
        earned = ref_earned_map.get(ref_code, 0)
        top_referrals.append((ref_code, invited, earned))

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
        f"💬 Всего сообщений: {total_messages}\n"
        f"💬 За 24 ч: {messages_24h}\n\n"
        f"🔗 Пришли по реф. ссылке: {referred_total}\n\n"
    )

    if top_referrals:
        stats += "🏆 ТОП-15 рефералов:\n"
        for ref_code, invited, earned in top_referrals:
            earned_rub = round((earned or 0) / 100, 2)
            stats += f"{ref_code} — {invited} чел., {earned_rub:.2f} ₽\n"

    return stats.strip()
