from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import traceback
import json
import aiogram
from aiogram.types import Update
from datetime import datetime, timedelta

# 🧠 Инициализация и основные объекты
from bot_instance import bot, dp

# 🧩 Импорты всех хэндлеров
from handlers import (
    gptchat,
    menu_handlers,
    aiogram_handlers,
    admin_handlers_aiogram,
    start_handlers,
    evening_handlers_aiogram  # важно, чтобы этот модуль был в handlers/
)

# 💳 CloudPayments
from cloudpayments import verify_signature

# 🗄️ База данных и модели
from database import SessionLocal
from models import get_user_by_telegram_id

# 🎨 Интерфейс
from ui import main_menu

# 🕯 Планировщики
from scheduler_affirmations import start_scheduler as start_affirmations
from scheduler_reactivation import start_scheduler as start_reactivation
from scheduler_evening_ritual import start_scheduler as start_evening_ritual

# ----------------------
# Подключаем роутеры
# ----------------------
dp.include_routers(
    admin_handlers_aiogram.router,  # ← всегда первым
    gptchat.router,
    menu_handlers.router,
    aiogram_handlers.router,
    start_handlers.router,
    evening_handlers_aiogram.router,  # ← теперь используется напрямую из импорта
)


# --- Создание таблиц при первом запуске ---
from database import engine, Base

print("🗄 Проверка и создание таблиц (если отсутствуют)...")
Base.metadata.create_all(bind=engine)
print("✅ Все таблицы синхронизированы.")

# --- Проверка и добавление недостающих колонок в таблицу users ---
from sqlalchemy import inspect, text

def add_missing_user_columns():
    with engine.connect() as conn:
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("users")]

        alter_statements = []

        # 🔗 Добавляем отсутствующие колонки по мере необходимости
        if "referrer_code" not in columns:
            alter_statements.append("ALTER TABLE users ADD COLUMN referrer_code VARCHAR;")
        if "referral_code" not in columns:
            alter_statements.append("ALTER TABLE users ADD COLUMN referral_code VARCHAR;")
        if "is_unlimited" not in columns:
            alter_statements.append("ALTER TABLE users ADD COLUMN is_unlimited BOOLEAN DEFAULT FALSE;")
        if "has_paid" not in columns:
            alter_statements.append("ALTER TABLE users ADD COLUMN has_paid BOOLEAN DEFAULT FALSE;")
        if "subscription_expires_at" not in columns:
            alter_statements.append("ALTER TABLE users ADD COLUMN subscription_expires_at TIMESTAMP;")
        if "first_seen_at" not in columns:
            alter_statements.append("ALTER TABLE users ADD COLUMN first_seen_at TIMESTAMP;")
        if "total_messages" not in columns:
            alter_statements.append("ALTER TABLE users ADD COLUMN total_messages INTEGER DEFAULT 0;")

        for stmt in alter_statements:
            print(f"🧩 Добавляем недостающую колонку: {stmt}")
            conn.execute(text(stmt))

        conn.commit()
        print("✅ Проверка и обновление структуры users завершено.")

add_missing_user_columns()

app = FastAPI()
print("💡 AIOGRAM VERSION:", aiogram.__version__)


# ----------------------
# Корневой эндпоинт
# ----------------------
@app.get("/")
async def root():
    return {"status": "ok"}


# ----------------------
# CloudPayments webhook
# ----------------------
@app.post("/payment/cloudpayments/result")
async def cloudpayments_result(request: Request):
    try:
        raw_body = await request.body()
        signature = request.headers.get("Content-HMAC", "")
        print("📦 RAW BODY:", raw_body.decode())

        if not verify_signature(raw_body, signature):
            return JSONResponse(content={"code": 1, "message": "Invalid signature"}, status_code=400)

        # Парсинг x-www-form-urlencoded
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

            current_expiry = user.subscription_expires_at or now
            base_date = max(current_expiry, now)
            user.subscription_expires_at = base_date + timedelta(days=days)

            # Реферальная логика
            if user.referrer_code:
                try:
                    referrer = get_user_by_telegram_id(db, str(user.referrer_code))
                    if referrer:
                        amount = float(data.get("Amount", "0").replace(",", "."))
                        reward = round(amount * 0.3, 2)
                        referrer.referral_earned = (referrer.referral_earned or 0.0) + reward
                        print(f"🎉 Начислено {reward}₽ рефералу {referrer.telegram_id}")
                except Exception as e:
                    print("⚠️ Ошибка при начислении бонуса:", e)

            db.commit()
            print(f"📆 Подписка продлена до: {user.subscription_expires_at}")

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


# ----------------------
# Telegram webhook
# ----------------------
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

# --- Запуск планировщиков рассылок ---

@app.on_event("startup")
async def startup_schedulers():
    """
    Запуск всех планировщиков (утренние аффирмации, реактивация, вечерний ритуал).
    """
    try:
        start_affirmations()
        print("✅ Affirmations scheduler подключен (ежедневно 09:00 Asia/Almaty)")
    except Exception as e:
        print("⚠️ Ошибка при запуске планировщика аффирмаций:", e)

    try:
        start_reactivation()
        print("✅ Reactivation scheduler подключен (ежедневно 22:00 Asia/Almaty)")
    except Exception as e:
        print("⚠️ Ошибка при запуске планировщика реактивации:", e)

    try:
        start_evening_ritual()
        print("✅ Evening ritual scheduler подключен (ежедневно 23:00 Asia/Almaty)")
    except Exception as e:
        print("⚠️ Ошибка при запуске вечернего ритуала:", e)


