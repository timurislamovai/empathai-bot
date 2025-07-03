from fastapi import APIRouter, Request
from starlette.responses import PlainTextResponse
import hashlib
import os
from database import SessionLocal
from models import get_user_by_telegram_id, update_user_subscription
from telegram import Bot

router = APIRouter()

ROBO_PASSWORD2 = os.environ["ROBO_PASSWORD2"]
REFERRAL_REWARD_PERCENT = 30  # % выплаты за реферала

bot = Bot(token=os.environ["TELEGRAM_TOKEN"])


@router.post("/payment/robokassa/result")
async def payment_result(request: Request):
    form = await request.form()

    out_summ = form.get("OutSum")
    inv_id = form.get("InvId")
    signature_value = form.get("SignatureValue", "").upper()
    telegram_id = form.get("shp_id")
    plan = form.get("shp_plan")

    signature_raw = f"{out_summ}:{inv_id}:{ROBO_PASSWORD2}:shp_id={telegram_id}:shp_plan={plan}"
    expected_signature = hashlib.md5(signature_raw.encode()).hexdigest().upper()

    if signature_value != expected_signature:
        return PlainTextResponse("bad signature", status_code=400)

    db = SessionLocal()
    user = get_user_by_telegram_id(db, telegram_id)
    if user:
        # ✅ Активируем подписку
        update_user_subscription(db, user, plan)

        # ✅ Отправляем уведомление
        bot.send_message(chat_id=telegram_id, text="🎉 Подписка активирована!")

        # 💸 Начисляем партнёрское вознаграждение
        if user.referrer_code:
            referrer = get_user_by_telegram_id(db, user.referrer_code)
            if referrer:
                reward = int(float(out_summ) * REFERRAL_REWARD_PERCENT / 100)
                referrer.ref_earned += reward
                referrer.ref_count += 1
                db.commit()

    return PlainTextResponse("OK")
