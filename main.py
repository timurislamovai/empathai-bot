from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from handlers import handle_update  # Импортируем только обработчик сообщений

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    try:
        return await handle_update(data)  # Обработка сообщения и лимитов в handlers.py
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
