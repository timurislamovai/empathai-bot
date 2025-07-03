from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from handlers import handle_update
from database import SessionLocal  # ✅ для подключения к БД
from payment_routes import router as payment_router
import traceback
from datetime import datetime

app = FastAPI()
app.include_router(payment_router)


@app.get("/")
async def root():
    return {"status": "ok"}


@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()

        # ✅ создаём сессию БД и передаём в handle_update
        db = SessionLocal()

        # ✅ вызываем обычную функцию — с await!
        await handle_update(data, db)  # ✅ ждём выполнения

        return {"ok": True}

    except Exception as e:
        print("❗ Ошибка в обработчике Webhook:")
        traceback.print_exc()
        try:
            with open("logs/error.log", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] ❌ Ошибка: {str(e)}\n")
        except:
            pass
        return JSONResponse(status_code=500, content={"error": str(e)})
