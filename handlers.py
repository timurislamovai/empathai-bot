from fastapi import FastAPI, Request
from config import TELEGRAM_TOKEN
from handlers import setup_webhook, handle_update
from models import Base, engine
from sqlalchemy.orm import Session

app = FastAPI()


@app.on_event("startup")
async def startup():
    # Создание таблиц, если их ещё нет
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы пересозданы")

    # Настройка Telegram webhook
    await setup_webhook()


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    await handle_update(data)
    return {"ok": True}


@app.get("/")
async def root():
    return {"status": "ok"}
