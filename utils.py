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
            all_data = json.load(f)
            return all_data.get(user_id, {})  # вернуть данные конкретного пользователя
    return {}

def save_user_data(user_id, data):
    all_data = {}
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            all_data = json.load(f)
    all_data[user_id] = data  # обновить данные пользователя
    with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
