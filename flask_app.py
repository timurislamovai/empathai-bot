from flask import Flask, request, jsonify
import os, openai, requests

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
openai.api_key = os.getenv("OPENAI_API_KEY")

SYSTEM_MESSAGE = (
    "Ты — виртуальный психолог и коуч от проекта EmpathAI. Твоя основная цель — "
    "оказывать информационную поддержку пользователям, помогать им справляться с эмоциональными трудностями..."
)

def process_update(update):
    user_message = update.get("message", {}).get("text")
    if not user_message:
        return None
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
            top_p=0.9
        )
        reply_text = response.choices[0].message.content.strip()
    except Exception as e:
        reply_text = "Ошибка при обращении к OpenAI: " + str(e)
    return reply_text

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    reply = process_update(update)
    if reply:
        chat_id = update.get("message", {}).get("chat", {}).get("id")
        if chat_id:
            send_message_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {"chat_id": chat_id, "text": reply}
            try:
                requests.post(send_message_url, json=payload)
            except Exception as e:
                print("Ошибка при отправке сообщения в Telegram:", e)
    return jsonify({"status": "Webhook received"})
