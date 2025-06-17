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
# Принимает сессию SQLAlchemy, возвращает готовый текст с данными:
# - всего пользователей
# - активные за 24 часа
# - новые за сегодня
# - неактивные более 7 дней
# - общее число сообщений
# - сообщения за последние 24 часа
def get_stats_summary(session):
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    # Общее количество зарегистрированных пользователей
    total_users = session.query(func.count(User.id)).scalar()

    # Количество пользователей, писавших за последние 24 часа
    active_24h = session.query(func.count(User.id)).filter(User.last_message_at >= day_ago).scalar()

    # Количество новых пользователей, пришедших сегодня
    new_today = session.query(func.count(User.id)).filter(func.date(User.first_seen_at) == now.date()).scalar()

    # Пользователи, неактивные более 7 дней
    inactive_7d = session.query(func.count(User.id)).filter(User.last_message_at < week_ago).scalar()

    # Общее количество отправленных сообщений всеми пользователями
    total_messages = session.query(func.sum(User.total_messages)).scalar() or 0

    # Количество сообщений за последние сутки
    messages_24h = session.query(func.sum(User.total_messages)).filter(User.last_message_at >= day_ago).scalar() or 0

    # Возврат текстовой статистики, готовой к отправке в Telegram
    return (
        f"📊 Статистика EmpathAI:\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"🟢 Активны за 24 ч: {active_24h}\n"
        f"🆕 Новые сегодня: {new_today}\n"
        f"💤 Неактивны (7+ дней): {inactive_7d}\n"
        f"💬 Всего сообщений: {total_messages}\n"
        f"💬 За 24 ч: {messages_24h}"
    )
