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

