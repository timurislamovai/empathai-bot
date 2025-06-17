import re

def clean_markdown(text):
    # Удаление жирного и курсивного
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)

    # Удаление заголовков (##, # и т.д.)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)

    # Удаление цитат ">"
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)

    # Замена маркеров списков (-, *) на •
    text = re.sub(r"^\s*[-*]\s+", "• ", text, flags=re.MULTILINE)

    return text
