# handlers/user_actions.py

from telegram import Bot
from sqlalchemy.orm import Session
from models import User
from referral import generate_cabinet_message
from ui import main_menu
from openai_api import reset_user_thread


def handle_personal_cabinet(user: User, chat_id: int, bot: Bot, db: Session):
    message_text, markup = generate_cabinet_message(user, str(user.telegram_id), db)
    bot.send_message(chat_id, message_text, reply_markup=markup)

def handle_reset(user: User, chat_id: int, bot: Bot, db: Session):
    reset_user_thread(db, user)
    bot.send_message(chat_id, "♻️ Диалог сброшен. Можешь начать новый разговор, и я забуду всё, что было сказано ранее.", reply_markup=main_menu())

def handle_about(chat_id: int, bot: Bot):
    bot.send_message(chat_id, "Я — Ила, ваш ИИ-собеседник. Готова поддержать в трудную минуту.", reply_markup=main_menu())

def handle_support(chat_id: int, bot: Bot):
    bot.send_message(chat_id, "ℹ️ Чтобы начать разговор, просто напишите, что у вас на душе. Я отвечу и постараюсь помочь 💬", reply_markup=main_menu())

def handle_terms(chat_id: int, bot: Bot):
    bot.send_message(chat_id, "Полные условия можно посмотреть на сайте: [ссылка]", reply_markup=main_menu())
