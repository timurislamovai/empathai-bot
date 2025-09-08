# openai_api.py

import openai
import os
from sqlalchemy.orm import Session
from models import User, update_user_thread_id

client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
ASSISTANT_ID = os.environ["ASSISTANT_ID"]

def send_message_to_assistant(thread_id: str | None, user_message: str) -> tuple[str, str]:
    if thread_id:
        thread = client.beta.threads.retrieve(thread_id)
    else:
        thread = client.beta.threads.create()

    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_message
    )

    # ⚡ добавляем ограничение по токенам
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=ASSISTANT_ID,
        max_output_tokens=60  # примерно 200 символов
    )

    while True:
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run.status == "completed":
            break
        elif run.status in ["failed", "cancelled", "expired"]:
            return "Что-то пошло не так. Попробуйте позже.", thread.id

    messages = client.beta.threads.messages.list(thread_id=thread.id)
    response = messages.data[0].content[0].text.value.strip()

    # ✂️ подстраховка: если ответ всё-таки длиннее 200 символов
    if len(response) > 200:
        response = response[:200].rstrip() + "… (ответ сокращён из-за лимита бесплатного тарифа)"

    return response, thread.id


def reset_user_thread(db: Session, user: User):
    user.thread_id = None
    db.commit()

