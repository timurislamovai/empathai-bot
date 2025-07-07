import requests
from requests.auth import HTTPBasicAuth

# 🔐 ВСТАВЬ СЮДА СВОИ ДАННЫЕ
PUBLIC_ID = "pk_5afc93bc88e1dbf81712b878a9da3"
API_PASSWORD = "8f43e273552073b0dc8fd5c5fbf83a05"

def generate_payment_link(telegram_id: str, plan: str, amount: int = 10000) -> str:
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
        response = requests.post(url, json=payload, auth=HTTPBasicAuth(PUBLIC_ID, API_PASSWORD))
        result = response.json()

        if result.get("Success") and "Model" in result:
            return result["Model"]["Url"]
        else:
            print("❌ Ошибка при создании ссылки:", result)
            return "Ошибка генерации ссылки"
    except Exception as e:
        print("❌ Исключение при запросе:", e)
        return "Ошибка подключения"

# 🧪 ТЕСТ
if __name__ == "__main__":
    link = generate_payment_link("944583273", "monthly")
    print("🔗 Ссылка на оплату:", link)
