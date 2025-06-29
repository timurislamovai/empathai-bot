# 1. Загрузка keywords.json
import json
import os

def load_topic_keywords(filename="keywords.json"):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ Файл keywords.json не найден.")
        return {}

# 2. Создаём глобальную переменную
TOPIC_KEYWORDS = load_topic_keywords()

def diagnose_topic(text):
    text = text.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(word in text for word in keywords):
            return topic
    return None

# 3. Определение темы
def generate_topic_hint(topic):
    hints = {
        "тревога": "Ты чувствуешь тревогу. Хочешь рассказать, что её вызывает?",
        "одиночество": "Ты чувствуешь себя одиноко? Расскажешь, когда ты начал это ощущать?",
        "выгорание": "Похоже, ты устал. Хочешь поговорить о том, что особенно изматывает?",
        "бессонница": "Тебе сложно уснуть? Расскажешь, как проходят ночи?",
        "грусть": "Ты грустишь. Хочешь поделиться, что вызывает это чувство?"
    }
    return hints.get(topic, "")


def load_crisis_words(filename="crisis_words.txt"):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return [line.strip().lower() for line in f if line.strip()]
    except FileNotFoundError:
        print("⚠️ Файл с кризисными словами не найден.")
        return []

CRISIS_WORDS = load_crisis_words()

def contains_crisis_words(text):
    text = text.lower()
    return any(word in text for word in CRISIS_WORDS)
