# handlers/chat_flow.py

from telegram import Bot
from sqlalchemy.orm import Session
from models import User
from openai_api import send_message_to_assistant, reset_user_thread
from utils import clean_markdown
from handlers.subscription_utils import increment_message_count

def process_user_message(user: User, text: str, chat_id: int, bot: Bot, db: Session):
    try:
        assistant_response, thread_id = send_message_to_assistant(user.thread_id, text)
        user.thread_id = thread_id
        increment_message_count(user)
        assistant_response = clean_markdown(assistant_response)
        bot.send_message(chat_id, assistant_response)
    except Exception as e:
        bot.send_message(chat_id, "⚠️ Произошла ошибка при обращении к ИИ. Попробуйте позже.")
