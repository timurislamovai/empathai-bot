from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from main_handlers import handle_update
from database import SessionLocal
import traceback

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

        db = SessionLocal()
        await handle_update(data, db)  # ← ДОБАВЛЕН await
        return {"ok": True}
    except Exception as e:
        print("❌ Ошибка в telegram_webhook:", e)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()


