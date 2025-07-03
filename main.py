from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from handlers import handle_update
from database import SessionLocal
import traceback

app = FastAPI()

# Платёжные маршруты
from payment_routes import router as payment_router
app.include_router(payment_router)

@app.get("/")
async def root():
    return {"status": "ok"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        db = SessionLocal()  # ✅ создаём сессию базы данных
        handle_update(data, db)  # ✅ передаём и update, и db
        return {"ok": True}
    except Exception as e:
        print("❌ Ошибка в telegram_webhook:", e)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()  # ✅ не забываем закрыть сессию
