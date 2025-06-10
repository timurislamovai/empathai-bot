import os
import json
import requests

JSONBIN_API_KEY = os.environ.get("JSONBIN_API_KEY")
BIN_ID = os.environ.get("JSONBIN_BIN_ID")

HEADERS = {
    "Content-Type": "application/json",
    "X-Master-Key": JSONBIN_API_KEY,
}

def load_text(filename):
    filepath = os.path.join("texts", f"{filename}.txt")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    return "Файл не найден."

def load_user_data():
    url = f"https://api.jsonbin.io/v3/b/{BIN_ID}/latest"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.json()["record"]
    except Exception as e:
        print("Ошибка загрузки данных:", e)
        return {}

def save_user_data(data):
    url = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
    try:
        response = requests.put(url, headers=HEADERS, json=data)
        response.raise_for_status()
        return True
    except Exception as e:
        print("Ошибка сохранения данных:", e)
        return False
