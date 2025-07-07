import os
import hmac
import hashlib
import base64
import requests
import json
from config import CLOUDPAYMENTS_SECRET, CLOUDPAYMENTS_PUBLIC_ID  # из Railway переменных

# ✅ Проверка подписи от CloudPayments
def verify_signature(body: bytes, received_signature: str) -> bool:
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
        "Content-HMAC": ""
    }

    data = {
        "Status": "Completed",
        "InvoiceId": "123456",
        "Amount": 1000,
        "Currency": "RUB",
        "Data": {
            "telegram_id": "944583273",
            "plan": "monthly"
        }
    }

    body = json.dumps(data, separators=(',', ':')).encode('utf-8')

    signature = base64.b64encode(
        hmac.new(
            CLOUDPAYMENTS_SECRET.encode(),
            body,
            hashlib.sha256
        ).digest()
    ).decode()

    headers["Content-HMAC"] = signature

    response = requests.post(url, headers=headers, data=body)
    print("📤 Тестовая отправка завершена:")
    print("🧾 Статус:", response.status_code)
    print("📨 Ответ сервера:", response.text)


# ✅ Генерация платёжной ссылки (добавлено)
def generate_payment_link(telegram_id: str, plan: str, amount: int = 10000) -> str:
    """
    Генерирует платёжную ссылку CloudPayments с параметрами:
    - telegram_id: Telegram ID пользователя
    - plan: 'monthly' или 'yearly'
    - amount: сумма в копейках (10000 = 100.00 руб.)
    """
    url = "https://api.cloudpayments.ru/orders/create"

    payload = {
        "Amount": amount / 100,
        "Currency": "RUB",
        "InvoiceId": f"sub_{telegram_id}_{plan}",
        "Description": f"Подписка {plan}",
        "AccountId": str(telegram_id),
        "Data": {
            "telegram_id": str(telegram_id),
            "plan": plan
        }
    }

    try:
        response = requests.post(url, json=payload, auth=requests.auth.HTTPBasicAuth(CLOUDPAYMENTS_PUBLIC_ID, CLOUDPAYMENTS_SECRET))
        result = response.json()

        if result.get("Success") and "Model" in result:
            print("✅ Ссылка создана:", result["Model"]["Url"])
            return result["Model"]["Url"]
        else:
            print("❌ Ошибка при создании ссылки:", result)
            return "Ошибка генерации ссылки"
    except Exception as e:
        print("❌ Исключение при запросе:", e)
        return "Ошибка подключения"
