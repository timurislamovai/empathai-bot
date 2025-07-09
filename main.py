from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import traceback
import json
from aiogram.types import Update
import aiogram
from handlers import admin_panel_api

from bot_instance import bot, dp
from handlers import gptchat, menu_handlers, aiogram_handlers, admin_handlers_aiogram
from cloudpayments import verify_signature
from database import SessionLocal
from models import get_user_by_telegram_id
from datetime import datetime, timedelta
from ui import main_menu

# Сначала создаём FastAPI-приложение
app = FastAPI()
print("💡 AIOGRAM VERSION:", aiogram.__version__)

# Подключаем API для админ-панели
app.include_router(admin_panel_api.router)

# Подключаем Telegram-обработчики
dp.include_routers(
    admin_handlers_aiogram.router,
    gptchat.router,
    menu_handlers.router,
    aiogram_handlers.router
)


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

        # ✅ Парсинг x-www-form-urlencoded
        from urllib.parse import parse_qs
        parsed = parse_qs(raw_body.decode())
        data = {k: v[0] for k, v in parsed.items()}

        print("✅ Подпись CloudPayments подтверждена.")
        print("📨 Распознанные данные:", data)

        if data.get("Status") != "Completed":
            print("⚠️ Платёж не завершён:", data.get("Status"))
            return {"code": 0}

        # Получение telegram_id и плана
        telegram_id = None
        plan = None
        raw_data = data.get("Data")

        if raw_data:
            try:
                parsed_data = json.loads(raw_data)
                telegram_id = parsed_data.get("telegram_id")
                plan = parsed_data.get("plan")
            except Exception as e:
                print("⚠️ Ошибка при парсинге поля Data:", e)

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
        
            # 🔄 Правильное продление подписки
            current_expiry = user.subscription_expires_at or now
            base_date = max(current_expiry, now)
            user.subscription_expires_at = base_date + timedelta(days=days)
        
            db.commit()  # 💾 Сохраняем изменения!
        
            print(f"📆 Подписка продлена до: {user.subscription_expires_at}")



            # ✅ Реферальная логика
            if user.referrer_code:
                try:
                    referrer = get_user_by_telegram_id(db, int(user.referrer_code))
                    if referrer:
                        amount = float(data.get("Amount", "0").replace(",", "."))  # сумма оплаты
                        reward = round(amount * 0.3, 2)  # 30% бонус

                        referrer.ref_count += 1
                        referrer.ref_earned += int(reward * 100)  # сохраняем в копейках

                        print(f"💸 Начислено {reward}₽ рефералу {referrer.telegram_id}")
                        db.commit()
                except Exception as e:
                    print("⚠️ Ошибка начисления реферального бонуса:", e)

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


@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        print("✅ /webhook вызван\n📨 Raw data:", data)

        update = Update(**data)
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        print("❌ Ошибка в webhook:", e)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
