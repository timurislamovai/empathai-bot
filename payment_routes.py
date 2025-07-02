from fastapi import APIRouter, Request
from starlette.responses import PlainTextResponse
import hashlib
import os
from database import SessionLocal
from models import get_user_by_telegram_id, update_user_subscription

router = APIRouter()

ROBO_PASSWORD2 = os.environ["ROBO_PASSWORD2"]

@router.post("/payment/robokassa/result")
async def payment_result(request: Request):
    form = await request.form()

    out_summ = form.get("OutSum")
    inv_id = form.get("InvId")
    signature_value = form.get("SignatureValue", "").upper()
    telegram_id = form.get("shp_id")
    plan = form.get("shp_plan")

    # ❗ Новый порядок — сначала пароль, потом shp_ параметры
    signature_raw = f"{out_summ}:{inv_id}:{ROBO_PASSWORD2}:shp_id={telegram_id}:shp_plan={plan}"
    expected_signature = hashlib.md5(signature_raw.encode()).hexdigest().upper()

    if signature_value != expected_signature:
        return PlainTextResponse("bad sign", status_code=400)

    # Обновляем пользователя
    db = SessionLocal()
    user = get_user_by_telegram_id(db, telegram_id)

    if user:
        update_user_subscription(db, user, plan)
        db.commit()

    return PlainTextResponse("OK")
