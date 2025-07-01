

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from handlers import handle_update  # Импортируем только обработчик сообщений
import traceback
from datetime import datetime

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        return await handle_update(data)  # Обработка сообщения и лимитов в handlers.py
    except Exception as e:
        print("❗ Ошибка в обработчике Webhook:")
        traceback.print_exc()
        try:
            with open("logs/error.log", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] ❌ Ошибка: {str(e)}\n")
        except:
            pass
        return JSONResponse(status_code=500, content={"error": str(e)})
