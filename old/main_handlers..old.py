import os
import time
from openai_api import send_message_to_assistant
from handlers.message_router import handle_command, handle_menu_button
from ui import main_menu
from datetime import datetime
from models import User
from ui import subscription_plan_keyboard
from telegram import Bot, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from database import SessionLocal
from models import (
    get_user_by_telegram_id,
    create_user,
    update_user_thread_id,
    increment_message_count,
    reset_user_thread
)

bot = Bot(token=os.environ["TELEGRAM_TOKEN"])

async def handle_update(update, db):
    print("👉 handle_update вызван")
    message = update.get("message")
    if not message:
        return

    text = message.get("text", "")
    chat_id = message["chat"]["id"]
    telegram_id = str(message["from"]["id"])

    db = SessionLocal()
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        user = create_user(db, telegram_id)

    if text.startswith("/"):
        await handle_command(text, user, chat_id, bot, db)
        return

    await handle_menu_button(text, user, chat_id, bot, db)
    return
