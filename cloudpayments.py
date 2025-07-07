import hmac
import hashlib
import base64
import os

CLOUDPAYMENTS_SECRET = os.environ.get("CLOUDPAYMENTS_SECRET")  # Зададим позже в .env

def verify_signature(body: bytes, received_signature: str) -> bool:
    """
    Проверка подписи Content-HMAC
    :param body: Тело запроса в байтах
    :param received_signature: Подпись из заголовка Content-HMAC
    :return: True, если подпись корректна
    """
    if not CLOUDPAYMENTS_SECRET:
        return False

    secret = CLOUDPAYMENTS_SECRET.encode("utf-8")
    computed_signature = base64.b64encode(
        hmac.new(secret, body, digestmod=hashlib.sha256).digest()
    ).decode()

    return computed_signature == received_signature

import requests
import json

def send_test_payment():
    url = "https://empathai-bot-production.up.railway.app/payment/cloudpayments/result"
    headers = {
        "Content-Type": "application/json",
        "Content-HMAC": ""  # пока оставим пустым
    }

    data = {
        "Status": "Completed",
        "InvoiceId": "123456",
        "Amount": 1000,
        "Currency": "RUB",
        "Data": {
            "telegram_id": "944583273",  # 👈 замени на свой ID
            "plan": "monthly"
        }
    }

    # Создаём подпись (HMAC-SHA256 от тела, как в CloudPayments)
    import hmac
    import hashlib
    from config import CLOUDPAYMENTS_SECRET  # 👈 ключ из .env

    body = json.dumps(data, separators=(',', ':')).encode('utf-8')
    signature = hmac.new(
        CLOUDPAYMENTS_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    headers["Content-HMAC"] = signature

    response = requests.post(url, headers=headers, data=body)
    print("✅ Ответ от сервера:", response.status_code)
    print(response.text)
