import os
from sqlalchemy.orm import sessionmaker
from models import User
from db import engine

# Создание сессии для работы с базой данных
Session = sessionmaker(bind=engine)

def load_text(filename):
    filepath = os.path.join("texts", f"{filename}.txt")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    return "Файл не найден."

def get_user(telegram_id):
    session = Session()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    session.close()
    return user

def save_user(telegram_id, thread_id):
    session = Session()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if user:
        user.thread_id = thread_id
    else:
        user = User(telegram_id=telegram_id, thread_id=thread_id)
        session.add(user)
    session.commit()
    session.close()

def reset_thread(telegram_id):
    session = Session()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if user:
        user.thread_id = None
        session.commit()
    session.close()
