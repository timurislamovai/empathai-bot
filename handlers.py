async def handle_update(update):
    print("➡️ Получен апдейт:", update)

    if "message" not in update:
        return {"ok": True}

    chat_id = update["message"]["chat"]["id"]
    user_message = update["message"].get("text", "")

    db = SessionLocal()
    user = get_or_create_user(db, str(chat_id))

    # ✅ обработка команды сброса
    if user_message.lower() == "сбросить диалог":
        user.thread_id = None
        db.commit()
        send_message(chat_id, "🌀 Диалог сброшен. Я готов начать сначала 🌱", show_menu=True)
        db.close()
        return {"ok": True}

    # проверка лимита
    if user.free_messages_used >= FREE_MESSAGES_LIMIT:
        send_message(chat_id, "🔒 Превышен лимит бесплатных сообщений. Чтобы продолжить, оформите подписку.")
        db.close()
        return {"ok": True}

    try:
        if not user.thread_id:
            thread = openai.beta.threads.create()
            user.thread_id = thread.id
            db.commit()
            print("📌 Создан новый thread_id:", thread.id)

        openai.beta.threads.messages.create(
            thread_id=user.thread_id,
            role="user",
            content=user_message
        )

        run = openai.beta.threads.runs.create(
            thread_id=user.thread_id,
            assistant_id=ASSISTANT_ID
        )

        while True:
            run_status = openai.beta.threads.runs.retrieve(thread_id=user.thread_id, run_id=run.id)
            if run_status.status == "completed":
                break

        messages = openai.beta.threads.messages.list(thread_id=user.thread_id)
        assistant_reply = messages.data[0].content[0].text.value

        user.free_messages_used += 1
        db.commit()

    except Exception as e:
        print("❌ Ошибка при обращении к OpenAI:", str(e))
        assistant_reply = "Произошла ошибка. Попробуйте позже."

    db.close()
    def send_message(chat_id, text, show_menu=False):
        reply_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": text,
        }
    
        if show_menu:
            payload["reply_markup"] = {
                "keyboard": [
                    [{"text": "Личный кабинет"}, {"text": "Гид по боту"}],
                    [{"text": "Сбросить диалог"}]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
    
        requests.post(reply_url, json=payload)
        return {"ok": True}
