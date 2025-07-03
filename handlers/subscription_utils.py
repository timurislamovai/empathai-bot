from datetime import date, datetime
from sqlalchemy.orm import Session
from models import User

FREE_MESSAGES_LIMIT = 50  # или подгружай из env

def is_subscription_active(user: User) -> bool:
    return user.has_paid and user.subscription_expires_at and user.subscription_expires_at > datetime.utcnow()

def check_and_update_daily_limit(db: Session, user: User):
    today = date.today()
    if user.last_message_date != today:
        user.free_messages_used = 0
        user.last_message_date = today
        db.commit()

def can_send_free_message(user: User) -> bool:
    return user.free_messages_used < FREE_MESSAGES_LIMIT

def increment_message_count(db: Session, user: User):
    user.free_messages_used += 1
    db.commit()
