# handlers/crisis_log.py

from models import User
from datetime import datetime

CRISIS_WORDS = [
    "самоубийство", "умереть", "покончить", "повеситься", "сдохнуть", "не хочу жить", 
    "ушёл бы", "не вижу смысла", "устал от жизни", "хочу исчезнуть"
]

def contains_crisis_words(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in CRISIS_WORDS)

async def log_crisis_message(user: User, text: str):
    log_entry = (
        f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] "
        f"User ID: {user.telegram_id} — Message: {text}\n"
    )
    with open("logs/crisis_log.txt", "a", encoding="utf-8") as file:
        file.write(log_entry)
