from datetime import datetime

# Ключевые фразы
HIGH_RISK = [
    "не хочу жить", "покончить с собой", "хочу умереть",
    "смысла больше нет", "суицид", "убить себя"
]

MEDIUM_RISK = [
    "я не справляюсь", "очень тяжело", "не могу больше", "устал от жизни",
    "всё рушится", "не вижу выхода", "опустились руки"
]

LOW_RISK = [
    "ничего не хочется", "устал", "потерял интерес", "нет мотивации"
]

SAFE_PHRASES = [
    "умереть от смеха", "сдохнуть со смеху", "не хочу жить в лжи"
]


def classify_crisis_level(text: str) -> str:
    text = text.lower()

    if any(phrase in text for phrase in SAFE_PHRASES):
        return "none"

    if any(phrase in text for phrase in HIGH_RISK):
        return "high"

    if any(phrase in text for phrase in MEDIUM_RISK):
        return "medium"

    if any(phrase in text for phrase in LOW_RISK):
        return "low"

    return "none"


def log_crisis_message(user_id: str, message: str, level: str = "MEDIUM"):
    with open("crisis_log.txt", "a", encoding="utf-8") as log_file:
        log_file.write(
            f"[{datetime.now()}] Level: {level.upper()} | Telegram ID: {user_id} | Message: {message}\n"
        )
