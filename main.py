from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import traceback
from aiogram.types import Update
import aiogram

from bot_instance import bot, dp
from handlers import gptchat, menu_handlers, aiogram_handlers, admin_handlers_aiogram
from cloudpayments import verify_signature  # 🔹 добавлено

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

# 🔹 Новый маршрут для обработки CloudPayments уведомлений
@app.post("/payment/cloudpayments/result")
async def cloudpayments_result(request: Request):
    body = await request.body()
    signature = request.headers.get("Content-HMAC")

    if not signature or not verify_signature(body, signature):
        return JSONResponse(content={"code": 13, "message": "Invalid signature"}, status_code=400)

    # Пока просто подтверждаем получение
    return JSONResponse(content={"code": 0})
