from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import traceback
from aiogram.types import Update
import aiogram

from bot_instance import bot, dp
from handlers import gptchat, menu_handlers, aiogram_handlers, admin_handlers_aiogram

# Подключаем все роутеры
dp.include_routers(
    gptchat.router,
    menu_handlers.router,
    aiogram_handlers.router
)

app = FastAPI()

print("💡 AIOGRAM VERSION:", aiogram.__version__)


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
