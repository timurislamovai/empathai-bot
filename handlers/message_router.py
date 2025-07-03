# handlers/message_router.py

from telegram import Bot
from sqlalchemy.orm import Session
from models import User

def handle_command(text: str, user: User, chat_id: int, bot: Bot, db: Session):
    # Здесь в будущем будет обработка команд
    pass

def handle_menu_button(text: str, user: User, chat_id: int, bot: Bot, db: Session):
    # Здесь будет обработка кнопок, таких как "Личный кабинет", "Купить подписку" и т.д.
    pass
