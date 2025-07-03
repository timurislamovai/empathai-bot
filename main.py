from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from handlers import handle_update  # Импорт обработчика
import traceback

app = FastAPI()

# Подключаем платежные маршруты
from payment_routes import router as payment_router
app.include_router(payment_router)

@app.get("/")
async def root():
    return {"status": "ok"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        handle_update(data)  # ❗ ВАЖНО: синхронный вызов
        return {"ok": True}
    except Exception as e:
        print("❌ Ошибка в telegram_webhook:", e)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
