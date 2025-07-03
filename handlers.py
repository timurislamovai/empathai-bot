from handlers.message_router import handle_command, handle_menu_button
from robokassa import generate_payment_url
from ui import main_menu
import os
import time
from datetime import datetime
from models import User
from filters import classify_crisis_level, log_crisis_message
from referral import generate_cabinet_message, generate_withdraw_info
from admin_commands import handle_admin_stats
from telegram import Bot, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from utils import clean_markdown
from models import (
    get_user_by_telegram_id,
    create_user,
    update_user_thread_id,
    increment_message_count,
    reset_user_thread
)
from openai_api import send_message_to_assistant

ADMIN_IDS = ["944583273", "396497806"]
bot = Bot(token=os.environ["TELEGRAM_TOKEN"])
FREE_MESSAGES_LIMIT = int(os.environ.get("FREE_MESSAGES_LIMIT", 50))


def subscription_plan_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🗓 Купить на 1 месяц"), KeyboardButton("📅 Купить на 1 год")],
            [KeyboardButton("🔙 Назад в главное меню")]
        ],
        resize_keyboard=True
    )

def handle_update(update):
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
        handle_command(text, user, chat_id, bot, db)
    else:
        handle_menu_button(text, user, chat_id, bot, db)

