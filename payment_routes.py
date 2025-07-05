print("🔁 payment_routes.py загружен")

from fastapi import APIRouter, Request
from starlette.responses import PlainTextResponse
from models import get_user_by_telegram_id
from database import SessionLocal
from telegram import Bot
import os
import hashlib
from datetime import datetime, timedelta

router = APIRouter()

ROBO_PASSWORD2 = os.environ["ROBO_PASSWORD2"]
REFERRAL_REWARD_PERCENT = 30
bot = Bot(token=os.environ["TELEGRAM_TOKEN"])

@router.post("/payment/robokassa/test")
async def payment_test(request: Request):
    print("✅ test POST получен")
    return PlainTextResponse("OK")

    out_summ = float(form.get("OutSum"))
    out_summ_str = "{:.0f}".format(out_summ)
    inv_id = form.get("InvId")
    signature_value = form.get("SignatureValue", "").upper()
    telegram_id = str(form.get("shp_id"))
    plan = form.get("shp_plan")
    
    signature_raw = f"{out_summ_str}:{inv_id}:{ROBO_PASSWORD2}:shp_id={telegram_id}:shp_plan={plan}"
    expected_signature = hashlib.md5(signature_raw.encode()).hexdigest().upper()
    
    print(f"[🧾] signature_raw = {signature_raw}")
    print(f"[✅] expected_signature = {expected_signature}")
    print(f"[📨] received_signature = {signature_value}")


    if signature_value != expected_signature:
        return PlainTextResponse("bad sign", status_code=400)

    db = SessionLocal()
    user = get_user_by_telegram_id(db, telegram_id)
    print(f"📥 Получен telegram_id из Robokassa: {telegram_id} (тип: {type(telegram_id)})")

    if not user:
        print(f"❌ Пользователь не найден в БД по telegram_id = {telegram_id}")
        return PlainTextResponse("user not found", status_code=404)
    else:
        print(f"✅ Пользователь найден: {user.telegram_id}")

    # Активируем подписку
    user.has_paid = True
    user.subscription_expires_at = datetime.utcnow() + timedelta(days=30)
    db.commit()

    # Реферальное начисление
    if user.referrer_code and user.referrer_code.isdigit():
        ref_user = get_user_by_telegram_id(db, user.referrer_code)
        if ref_user:
            reward = int(out_summ * REFERRAL_REWARD_PERCENT / 100)
            ref_user.ref_earned += reward
            ref_user.ref_count += 1
            db.commit()

    # Сообщение пользователю
    try:
        bot.send_message(chat_id=int(telegram_id), text="🎉 Подписка активирована! Спасибо за оплату.")
    except Exception as e:
        print("Ошибка при отправке сообщения:", e)
