# main.py

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import traceback
from aiogram.types import Update

from bot_instance import bot, dp

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        print("📥 Получено сообщение из Telegram:")
        print(data)

        update = Update(**data)
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        print("❌ Ошибка в telegram_webhook:", e)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
