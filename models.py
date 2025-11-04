from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Float, Boolean, Date
from database import Base
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# ---------- ПОЛЬЗОВАТЕЛИ ----------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)
    thread_id = Column(String)
    free_messages_used = Column(Integer, default=0)
    last_message_date = Column(Date, default=None)

    # 💳 Подписка и тариф
    has_paid = Column(Boolean, default=False)
    is_unlimited = Column(Boolean, default=False)
    subscription_expires_at = Column(DateTime, nullable=True)

    # 💸 Финансы и рефералы
    referral_earned = Column(Float, default=0.0)
    referral_paid = Column(Float, default=0.0)
    referrer_code = Column(String, nullable=True)   # кто пригласил
    referral_code = Column(String, nullable=True)   # собственный код пользователя

    # 🕒 Логирование
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    total_messages = Column(Integer, default=0)


# ---------- ВЕЧЕРНИЙ РИТУАЛ ----------
class EveningRitualLog(Base):
    __tablename__ = "evening_ritual_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    emotion = Column(String, nullable=True)
    action = Column(String, nullable=False)
    is_premium = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
def get_user_by_telegram_id(db: Session, telegram_id: int):
    return db.query(User).filter(User.telegram_id == telegram_id).first()


def create_user(db: Session, telegram_id: int, referrer_code: str = None):
    user = User(
        telegram_id=telegram_id,
        referrer_code=referrer_code,
        first_seen_at=datetime.utcnow(),
        free_messages_used=0,
        total_messages=0,
        thread_id=None
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_thread_id(db: Session, user: User, thread_id: str):
    user.thread_id = thread_id
    db.commit()


def increment_message_count(db: Session, user: User):
    user.free_messages_used += 1
    db.commit()


def reset_user_thread(db: Session, user: User):
    user.thread_id = None
    db.commit()


def update_user_subscription(db: Session, user: User, plan: str):
    now = datetime.utcnow()
    if plan == "monthly":
        expires = now + timedelta(days=30)
    elif plan == "yearly":
        expires = now + timedelta(days=365)
    else:
        expires = now
    user.has_paid = True
    user.subscription_expires_at = expires
    user.free_messages_used = 0
    db.commit()


# ---------- СТАТИСТИКА ВЫБОРА ТЕМ ----------
class TopicStat(Base):
    __tablename__ = "topic_stats"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, unique=True)
    count = Column(Integer, default=0)


def increment_topic_stat(db: Session, topic_key: str):
    stat = db.query(TopicStat).filter_by(topic=topic_key).first()
    if not stat:
        stat = TopicStat(topic=topic_key, count=1)
        db.add(stat)
    else:
        stat.count += 1
    db.commit()


def get_all_stats(db: Session):
    return db.query(TopicStat).all()
