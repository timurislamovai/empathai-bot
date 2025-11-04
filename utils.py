import re
from datetime import datetime, timedelta
from sqlalchemy import func
from models import User
from database import SessionLocal


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

    try:
        # --- Общие данные ---
        total_users = session.query(func.count(User.id)).scalar()

        new_today = session.query(func.count(User.id)).filter(
            (User.first_seen_at != None) & (func.date(User.first_seen_at) == now.date())
        ).scalar()

        new_7d = session.query(func.count(User.id)).filter(
            (User.first_seen_at != None) & (User.first_seen_at >= week_ago)
        ).scalar()

        new_30d = session.query(func.count(User.id)).filter(
            (User.first_seen_at != None) & (User.first_seen_at >= month_ago)
        ).scalar()

        # --- Активность ---
        active_24h = session.query(func.count(User.id)).filter(
            (User.last_message_date != None) & (User.last_message_date >= day_ago.date())
        ).scalar()

        active_7d = session.query(func.count(User.id)).filter(
            (User.last_message_date != None) & (User.last_message_date >= week_ago.date())
        ).scalar()

        inactive = session.query(func.count(User.id)).filter(
            (User.last_message_date == None) | (User.last_message_date < week_ago.date())
        ).scalar()

        # --- Подписки ---
        paid_total = session.query(func.count(User.id)).filter(User.has_paid == True).scalar()
        free_total = session.query(func.count(User.id)).filter(User.has_paid == False).scalar()

        paid_7d = session.query(func.count(User.id)).filter(
            (User.has_paid == True) & (User.first_seen_at >= week_ago)
        ).scalar()

        paid_30d = session.query(func.count(User.id)).filter(
            (User.has_paid == True) & (User.first_seen_at >= month_ago)
        ).scalar()

        # --- Бесплатный лимит ---
        expired_trial = session.query(User).filter(
            (User.free_messages_used >= 7),
            (User.has_paid == False),
            (User.is_unlimited == False)
        ).count()

        # --- Реферальная активность ---
        referred_users = session.query(func.count(User.id)).filter(
            User.referrer_code != None
        ).scalar()

        # --- Формирование итогового текста ---
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
            f"✅ Активных (за 7 дней): {active_7d}\n"
            f"⚡ Активных за 24ч: {active_24h}\n\n"
            f"❗ Закончился лимит (7 сообщений): {expired_trial}\n"
            f"🔗 Пришли по реф. ссылке: {referred_users}\n"
        )

        return stats.strip()

    except Exception as e:
        print("❌ Ошибка в get_stats_summary:", e)
        return "⚠️ Ошибка при подсчёте статистики."


# ---------- Проверка подписки пользователя ----------
def is_user_premium(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь премиум-подписчиком.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            return False
        return bool(user.has_paid or user.is_unlimited)
    except Exception as e:
        print(f"Ошибка проверки Premium: {e}")
        return False
    finally:
        db.close()
