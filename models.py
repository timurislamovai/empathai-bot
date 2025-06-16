from sqlalchemy import Column, Integer, String, DateTime
from db import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    thread_id = Column(String, nullable=True)
    free_messages_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

from sqlalchemy.orm import Session

def get_user_by_telegram_id(db: Session, telegram_id: str):
    return db.query(User).filter(User.telegram_id == telegram_id).first()

def create_user(db: Session, telegram_id: str):
    user = User(telegram_id=telegram_id)
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
    user.free_messages_used = 0
    db.commit()
