import json
import os

USER_DATA_FILE = "users.json"

def load_text(filename):
    filepath = os.path.join("texts", f"{filename}.txt")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    return "Файл не найден."

def load_user_data(user_id):
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(user_id, {})  # Возвращаем только данные по user_id
    return {}

def save_user_data(user_id, user_data):
    data = {}
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

    data[user_id] = user_data  # Обновляем или добавляем пользователя

    with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
