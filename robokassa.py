import os
import hashlib
import urllib.parse

# Загружаем переменные из окружения
ROBO_LOGIN = os.environ["ROBO_LOGIN"]
ROBO_PASSWORD1 = os.environ["ROBO_PASSWORD1"]

# Цены подписки (в рублях)
PLAN_PRICES = {
    "monthly": 1199,
    "yearly": 11999
}

def generate_payment_url(telegram_id: str, invoice_id: int, plan: str) -> str:
    """
    Генерирует платёжную ссылку Robokassa для выбранного плана.
    
    :param telegram_id: Telegram ID пользователя
    :param invoice_id: Уникальный ID счёта (можно использовать timestamp или ID пользователя)
    :param plan: 'monthly' или 'yearly'
    :return: URL для оплаты через Robokassa
    """
    if plan not in PLAN_PRICES:
        raise ValueError("Недопустимый тип плана. Используй 'monthly' или 'yearly'.")

    out_summ = str(PLAN_PRICES[plan])
    description = "Подписка на EmpathAI: 1 месяц" if plan == "monthly" else "Подписка на EmpathAI: 1 год"

    # Формируем подпись: Login:OutSum:InvId:Password1
    signature_raw = f"{ROBO_LOGIN}:{out_summ}:{invoice_id}:{ROBO_PASSWORD1}"
    signature = hashlib.md5(signature_raw.encode()).hexdigest()

    # Дополнительные параметры shp_ — Robokassa их сохраняет и возвращает при callback
    params = {
        "MerchantLogin": ROBO_LOGIN,
        "OutSum": out_summ,
        "InvId": invoice_id,
        "Description": description,
        "SignatureValue": signature,
        "Culture": "ru",
        "Encoding": "utf-8",
        "IsTest": 0,
        "shp_id": telegram_id,
        "shp_plan": plan
    }

    base_url = "https://auth.robokassa.ru/Merchant/Index.aspx"
    return f"{base_url}?{urllib.parse.urlencode(params)}"
