from sqlalchemy import Column, Integer, BigInteger, String, DateTime
from database import Base
from datetime import datetime
from sqlalchemy.orm import Session

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)
    thread_id = Column(String)
    free_messages_used = Column(Integer, default=0)
    
    
    # 👇 Дополнительные поля для аналитики:
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow)
    total_messages = Column(Integer, default=0)

    
    referrer_code = Column(String, nullable=True)    # Новое поле для хранения реферального кода пригласившего пользователя
    created_at = Column(DateTime, default=datetime.utcnow)  # Дата регистрации пользователя (нужна для подсчёта рефералов за месяц)

    balance = Column(Float, default=0.0)       # Баланс пользователя (начисления от рефералов)
    total_earned = Column(Float, default=0.0)  # Сколько всего заработал


def get_user_by_telegram_id(db: Session, telegram_id: str):
    return db.query(User).filter(User.telegram_id == telegram_id).first()


# Добавлен параметр referrer_code, который сохраняется при создании пользователя
def create_user(db: Session, telegram_id: str, referrer_code: str = None):
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


def reset_user_thread(db: Session, user: User):
    user.thread_id = None
    db.commit()
