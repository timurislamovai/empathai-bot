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
from ui import main_menu  # если не подключен — нужно для reply_markup

# Подключаем роутеры
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
        print("✅ /webhook вызван")
        print("📨 Raw data:", data)

        update = Update(**data)
        try:
            await dp.feed_update(bot, update)
        except Exception as inner_error:
            print("❌ Ошибка в dp.feed_update:", inner_error)
            traceback.print_exc()

        return {"ok": True}
    except Exception as e:
        print("❌ Ошибка в telegram_webhook:", e)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/payment/cloudpayments/result")
async def cloudpayments_result(request: Request):
    try:
        raw_body = await request.body()
        signature = request.headers.get("Content-HMAC", "")

        if not verify_signature(raw_body, signature):
            return JSONResponse(content={"code": 1, "message": "Invalid signature"}, status_code=400)

        data = await request.json()
        print("✅ Успешная подпись CloudPayments:\n")
        print(data)

        status = data.get("Status")
        if status != "Completed":
            print("⚠️ Платёж не завершён:", status)
            return {"code": 0}

        # 🔎 Попытка достать данные
        telegram_id = None
        plan = None

        data_json_str = data.get("Data")
        if data_json_str:
            try:
                parsed_data = json.loads(data_json_str)
                telegram_id = parsed_data.get("telegram_id")
                plan = parsed_data.get("plan")
            except Exception as json_error:
                print("⚠️ Ошибка при парсинге поля Data:", json_error)

        # 🔄 Резерв — извлекаем из InvoiceId
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
        print(f"📦 План: {plan}")

        if not telegram_id or not plan:
            print("❌ Недостаточно данных для активации подписки.")
            return {"code": 0}

        # ✅ Активация подписки
        db = SessionLocal()
        user = get_user_by_telegram_id(db, str(telegram_id))
        if user:
            now = datetime.utcnow()
            days = 30 if plan == "monthly" else 365
            user.has_paid = True
            user.subscription_expires_at = now + timedelta(days=days)
            db.commit()
            print("✅ Подписка активирована.")
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
        return JSONResponse(content={"code": 2, "message": "Internal error"}, status_code=500)


from cloudpayments import send_test_payment


@app.get("/test-payment")
async def test_payment():
    send_test_payment()
    return {"status": "✅ Тестовое уведомление отправлено"}
