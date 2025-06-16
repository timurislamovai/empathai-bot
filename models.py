from sqlalchemy import Column, Integer, String, DateTime
from db import Base
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=False)
    thread_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
