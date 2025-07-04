from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Float, Boolean
from database import Base
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import Date

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)
    thread_id = Column(String)
    free_messages_used = Column(Integer, default=0)
    last_message_date = Column(Date, default=None)

    # 👇 Дополнительные поля для аналитики:
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow)
    total_messages = Column(Integer, default=0)

    referrer_code = Column(String, nullable=True)    # Реферальный код
    created_at = Column(DateTime, default=datetime.utcnow)

    # ✅ Новые поля для рефералов:
    ref_count = Column(Integer, default=0)
    ref_earned = Column(Integer, default=0)

    # ✅ Для безлимитного доступа
    is_unlimited = Column(Boolean, default=False)

    # ✅ Новые поля для подписки:
    has_paid = Column(Boolean, default=False)
    subscription_expires_at = Column(DateTime, nullable=True)


def get_user_by_telegram_id(db: Session, telegram_id: str):
    return db.query(User).filter(User.telegram_id == telegram_id).first()


def create_user(db: Session, telegram_id: int, referrer_code: str = None):
    user = User(
        telegram_id=telegram_id,
        referrer_code=referrer_code,
        first_seen_at=datetime.utcnow(),
        last_message_at=datetime.utcnow(),
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
last_message_date = Column(Date, default=None)

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
        expires = now  # fallback на случай ошибки

    user.has_paid = True
    user.subscription_expires_at = expires
    user.free_messages_used = 0
    db.commit()
