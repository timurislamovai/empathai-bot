# openai_api.py

import openai
import os
from sqlalchemy.orm import Session
from models import User, update_user_thread_id

client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
ASSISTANT_ID = os.environ["ASSISTANT_ID"]

def send_message_to_assistant(
    thread_id: str | None,
    user_message: str,
    is_paid: bool = False,
    is_unlimited: bool = False
) -> tuple[str, str]:
    # если у пользователя есть старый thread_id — берём его, иначе создаём новый
    if thread_id:
        thread = client.beta.threads.retrieve(thread_id)
    else:
        thread = client.beta.threads.create()

    # добавляем сообщение пользователя в поток
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_message
    )

    # запускаем ассистента (⚠️ без max_output_tokens — в Assistants API этого параметра нет)
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=ASSISTANT_ID
    )

    # ждём завершения работы
    while True:
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run.status == "completed":
            break
        elif run.status in ["failed", "cancelled", "expired"]:
            return "Что-то пошло не так. Попробуйте позже.", thread.id

    # получаем последний ответ ассистента
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    response = messages.data[0].content[0].text.value.strip()

    # ✂️ если пользователь бесплатный — обрезаем ответ до 200 символов
    if not is_paid and not is_unlimited and len(response) > 500:
        response = response[:500].rstrip() + "… (ответ сокращён из-за лимита бесплатного тарифа)"

    return response, thread.id

def reset_user_thread(db: Session, user: User):
    user.thread_id = None
    db.commit()
