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

