# openai_api.py

import openai
import os

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

    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=ASSISTANT_ID)

    while True:
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run.status == "completed":
            break
        elif run.status in ["failed", "cancelled", "expired"]:
            return "Что-то пошло не так. Попробуйте позже.", thread.id

    messages = client.beta.threads.messages.list(thread_id=thread.id)
    response = messages.data[0].content[0].text.value

    return response, thread.id
