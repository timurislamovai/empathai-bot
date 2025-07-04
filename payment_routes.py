import os
import hashlib
from fastapi import APIRouter, Request
from starlette.responses import PlainTextResponse
from models import update_user_subscription, get_user_by_telegram_id
from database import SessionLocal
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
    print(f"[💳] Оплата от Telegram ID: {telegram_id}")

    if user:
        print(f"[🔍] Пользователь найден: {user.telegram_id}")
        print(f"[🔍] План: {plan}")
        print(f"[🔍] Старая дата: {user.subscription_expires_at}")

    if not user:
        user = create_user(db, telegram_id)
        print(f"[➕] Новый пользователь создан: {telegram_id}")

        # ✅ Обновляем подписку
        update_user_subscription(db, user, plan)
        print(f"[✅] Подписка обновлена: {user.has_paid}, до {user.subscription_expires_at}")

        db.commit()

        # ✅ Отправляем уведомление пользователю
        message = (
            f"🎉 Подписка активирована до {user.subscription_expires_at.strftime('%d.%m.%Y')}!\n"
            f"Спасибо за поддержку. Теперь у тебя безлимитный доступ 🙌"
        )
        bot.send_message(chat_id=int(telegram_id), text=message)

        # 💸 Начисляем партнёрское вознаграждение
        if user.referrer_code:
            referrer = get_user_by_telegram_id(db, user.referrer_code)
            if referrer:
                reward = int(float(out_summ) * REFERRAL_REWARD_PERCENT / 100)
                referrer.ref_earned += reward
                referrer.ref_count += 1
                db.commit()

    return PlainTextResponse("OK")
