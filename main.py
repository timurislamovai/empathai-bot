from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import traceback
import json
from aiogram.types import Update
import aiogram

from bot_instance import bot, dp
from handlers import gptchat, menu_handlers, aiogram_handlers, admin_handlers_aiogram
from cloudpayments import verify_signature
from database import SessionLocal
from models import get_user_by_telegram_id
from datetime import datetime, timedelta
from ui import main_menu

# Подключаем роутеры
dp.include_routers(
    gptchat.router,
    menu_handlers.router,
    aiogram_handlers.router,
    admin_handlers_aiogram.router
)

app = FastAPI()
print("💡 AIOGRAM VERSION:", aiogram.__version__)


@app.get("/")
async def root():
    return {"status": "ok"}


@app.post("/payment/cloudpayments/result")
async def cloudpayments_result(request: Request):
    try:
        raw_body = await request.body()
        signature = request.headers.get("Content-HMAC", "")
        print("📦 RAW BODY:", raw_body.decode())

        if not verify_signature(raw_body, signature):
            return JSONResponse(content={"code": 1, "message": "Invalid signature"}, status_code=400)

        try:
            data = json.loads(raw_body.decode())
            print("✅ Успешная подпись CloudPayments")
            print("📨 Распознанные данные:", data)
        except Exception as json_error:
            print("❌ Не удалось распарсить тело JSON:", json_error)
            return JSONResponse(content={"code": 2, "message": "Invalid JSON"}, status_code=200)

        if data.get("Status") != "Completed":
            print("⚠️ Платёж не завершён:", data.get("Status"))
            return {"code": 0}

        # Получение telegram_id и плана
        telegram_id = None
        plan = None
        data_field = data.get("Data")

        if isinstance(data_field, dict):
            telegram_id = data_field.get("telegram_id")
            plan = data_field.get("plan")
        elif isinstance(data_field, str):
            try:
                parsed_data = json.loads(data_field)
                telegram_id = parsed_data.get("telegram_id")
                plan = parsed_data.get("plan")
            except Exception as e:
                print("⚠️ Ошибка при парсинге строки Data:", e)

        if not telegram_id or not plan:
            invoice_id = data.get("InvoiceId")
            if invoice_id and invoice_id.startswith("sub_"):
                try:
                    _, tid, pl = invoice_id.split("_")
                    telegram_id = tid
                    plan = pl
                except Exception as e:
                    print("⚠️ Не удалось извлечь данные из InvoiceId:", e)

        print(f"👤 Telegram ID: {telegram_id}")
        print(f"📦 План подписки: {plan}")

        if not telegram_id or not plan:
            print("❌ Недостаточно данных для активации подписки.")
            return {"code": 0}

        # Обновление пользователя
        db = SessionLocal()
        user = get_user_by_telegram_id(db, str(telegram_id))
        if user:
            now = datetime.utcnow()
            days = 30 if plan == "monthly" else 365
            user.has_paid = True
            user.subscription_expires_at = now + timedelta(days=days)
            db.commit()
            print("✅ Подписка активирована в БД.")
            try:
                await bot.send_message(
                    chat_id=int(telegram_id),
                    text="✅ Ваша подписка активирована!\nСпасибо за доверие 💙",
                    reply_markup=main_menu()
                )
            except Exception as send_err:
                print("⚠️ Не удалось отправить сообщение пользователю:", send_err)
        else:
            print("⚠️ Пользователь не найден в базе.")

        return {"code": 0}

    except Exception as e:
        print("❌ Ошибка при обработке данных CloudPayments:", e)
        traceback.print_exc()
        return JSONResponse(content={"code": 2, "message": "Internal error"}, status_code=500)
