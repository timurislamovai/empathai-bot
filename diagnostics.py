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
