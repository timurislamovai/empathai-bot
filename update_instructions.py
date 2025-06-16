# update_instructions.py
import os, requests
from dotenv import load_dotenv

load_dotenv()  # читает .env-файл в переменные окружения

ASSISTANT_ID = os.getenv("ASSISTANT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

resp = requests.patch(
    f"https://api.openai.com/v1/assistants/{ASSISTANT_ID}",
    headers={
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "instructions": (
            "Ты — виртуальный психолог EmpathAI. Отвечай по существу и не добавляй "
            "дисклеймеры. Только если вопрос выходит за рамки твоей компетенции "
            "(медицина, психиатрия, юридические вопросы и т. п.), добавляй в конце "
            "ответа: “⚠️ Я не являюсь специалистом в этой области. Если нужен профессиональный совет, обратитесь к соответствующему эксперту.”"
        )
    }
)
print("Status:", resp.status_code, resp.text)
