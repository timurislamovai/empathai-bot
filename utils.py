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
        User.free_messages_used >= 7,
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

        f"❗ Закончился лимит (7 сообщений): {expired_trial}\n\n"

        f"🔗 Пришли по реф. ссылке: {referred_users}\n"
    )
    return stats.strip()
    


# ---------- Проверка подписки пользователя ----------
from database import SessionLocal

def is_user_premium(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь премиум-подписчиком.
    Пока возвращает False (заглушка).
    В будущем можно будет проверять поле user.is_unlimited или has_paid.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            return False
        # 🔹 Здесь можно заменить на реальную проверку, если у пользователя есть поле тарифа:
        # return user.is_unlimited or user.has_paid
        return user.has_paid or user.is_unlimited  # если оба поля есть
    except Exception as e:
        print(f"Ошибка проверки Premium: {e}")
        return False
    finally:
        db.close()
