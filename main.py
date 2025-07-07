from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import traceback
from aiogram.types import Update
import aiogram

from bot_instance import bot, dp
from handlers import gptchat, menu_handlers, aiogram_handlers, admin_handlers_aiogram
from cloudpayments import verify_signature  # 🔹 добавлено
from database import SessionLocal
from models import get_user_by_telegram_id
from datetime import datetime, timedelta

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
        print("✅ /webhook вызван")  # ✅ ДОБАВЛЕНО
        print("📨 Raw data:", data)  # ✅ ДОБАВЛЕНО

        update = Update(**data)

        try:
            await dp.feed_update(bot, update)
        except Exception as inner_error:
            print("❌ Ошибка в dp.feed_update:", inner_error)  # ✅ ДОБАВЛЕНО
            traceback.print_exc()

        return {"ok": True}
    except Exception as e:
        print("❌ Ошибка в telegram_webhook:", e)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/payment/cloudpayments/result")
async def cloudpayments_result(request: Request):
    body = await request.body()
    signature = request.headers.get("Content-HMAC")

    if not signature or not verify_signature(body, signature):
        return JSONResponse(content={"code": 13, "message": "Invalid signature"}, status_code=400)

    try:
        data = await request.json()
        print("✅ Успешная подпись CloudPayments:")
        print(data)

        status = data.get("Status")
        telegram_id = data.get("Data", {}).get("telegram_id")
        plan = data.get("Data", {}).get("plan")

        print(f"🧾 Статус: {status}")
        print(f"👤 Telegram ID: {telegram_id}")
        print(f"📦 План: {plan}")

        if status == "Completed" and telegram_id and plan:
            db = SessionLocal()
            user = get_user_by_telegram_id(db, telegram_id)

            if user:
                user.has_paid = True
                if plan == "monthly":
                    user.subscription_expires_at = datetime.utcnow() + timedelta(days=30)
                elif plan == "yearly":
                    user.subscription_expires_at = datetime.utcnow() + timedelta(days=365)

                db.commit()
                print("✅ Подписка активирована.")

                try:
                    await bot.send_message(
                        chat_id=telegram_id,
                        text="✅ Ваша подписка активирована!\nСпасибо за оплату 💙"
                    )
                except Exception as e:
                    print(f"⚠️ Не удалось отправить сообщение пользователю {telegram_id}: {e}")

            return JSONResponse(content={"code": 0})

    except Exception as e:
        print("❌ Ошибка при обработке данных CloudPayments:", e)
        traceback.print_exc()
        return JSONResponse(content={"code": 99, "message": "Ошибка обработки"}, status_code=500)


# 👉 Вставь строго за пределами try/except и функций
from cloudpayments import send_test_payment


@app.get("/test-payment")
async def test_payment():
    send_test_payment()
    return {"status": "✅ Тестовое уведомление отправлено"}
