import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from handlers import setup_webhook, handle_update
from db import engine, Base

# Загрузка конфигурации из переменных окружения
TELEGRAM_TOKEN      = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY      = os.environ["OPENAI_API_KEY"]
ASSISTANT_ID        = os.environ["ASSISTANT_ID"]
DATABASE_URL        = os.environ["DATABASE_URL"]

# Лимит бесплатных сообщений (50 по умолчанию)
FREE_MESSAGES_LIMIT = int(os.environ.get("FREE_MESSAGES_LIMIT", 50))

app = FastAPI()

@app.on_event("startup")
async def startup():
    # Создаёт таблицы в базе (если ещё нет)
    Base.metadata.create_all(bind=engine)
    # Настраивает Telegram-webhook
    await setup_webhook()

@app.get("/")
async def root():
    return {"status": "ok"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    try:
        return await handle_update(data)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
