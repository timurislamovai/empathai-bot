import os
import hmac
import hashlib
import base64
import requests
import json
from config import CLOUDPAYMENTS_SECRET  # секрет берём из Railway переменной

# ✅ Проверка подписи от CloudPayments
def verify_signature(body: bytes, received_signature: str) -> bool:
    """
    Проверка подписи Content-HMAC
    :param body: Тело запроса в байтах
    :param received_signature: Подпись из заголовка Content-HMAC
    :return: True, если подпись корректна
    """
    if not CLOUDPAYMENTS_SECRET:
        print("❌ Переменная CLOUDPAYMENTS_SECRET не установлена.")
        return False

    secret = CLOUDPAYMENTS_SECRET.encode("utf-8")
    computed_signature = base64.b64encode(
        hmac.new(secret, body, digestmod=hashlib.sha256).digest()
    ).decode()

    if computed_signature == received_signature:
        print("✅ Подпись CloudPayments подтверждена.")
        return True
    else:
        print("❌ Подпись не совпадает.")
        print(f"🔎 Ожидалась: {computed_signature}")
        print(f"📥 Получена: {received_signature}")
        return False

# ✅ Тестовая отправка запроса (для ручной проверки webhook)
def send_test_payment():
    url = "https://empathai-bot-production.up.railway.app/payment/cloudpayments/result"
    headers = {
        "Content-Type": "application/json",
        "Content-HMAC": ""  # будет добавлена ниже
    }

    data = {
        "Status": "Completed",
        "InvoiceId": "123456",
        "Amount": 1000,
        "Currency": "RUB",
        "Data": {
            "telegram_id": "944583273",  # 👈 заменишь на нужный ID при тесте
            "plan": "monthly"
        }
    }

    body = json.dumps(data, separators=(',', ':')).encode('utf-8')

    # Генерация подписи (в формате base64 — как требует CloudPayments)
    signature = base64.b64encode(
        hmac.new(
            CLOUDPAYMENTS_SECRET.encode(),
            body,
            hashlib.sha256
        ).digest()
    ).decode()

    headers["Content-HMAC"] = signature

    # Отправка POST-запроса на твой webhook
    response = requests.post(url, headers=headers, data=body)
    print("📤 Тестовая отправка завершена:")
    print("🧾 Статус:", response.status_code)
    print("📨 Ответ сервера:", response.text)

from cloudpayments import send_test_payment  # убедись, что импорт есть

@app.get("/test-payment")
async def test_payment():
    send_test_payment()
    return {"status": "✅ Тестовое уведомление отправлено"}

