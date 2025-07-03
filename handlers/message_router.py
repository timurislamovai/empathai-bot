# handlers/message_router.py
from ui import main_menu, subscription_plan_keyboard
from referral import generate_cabinet_message
from utils import clean_markdown
from openai_api import send_message_to_assistant, reset_user_thread
from models import increment_message_count
from filters import contains_crisis_words, log_crisis_message



from telegram import Bot
from sqlalchemy.orm import Session
from models import User



def handle_command(text: str, user: User, chat_id: int, bot: Bot, db: Session):
    # Здесь в будущем будет обработка команд
    pass



def handle_menu_button(text, user, chat_id, bot, db):
    if text in ["👤 Личный кабинет", "👥 Кабинет", "Личный кабинет"]:
        message_text, markup = generate_cabinet_message(user, str(user.telegram_id), db)
        bot.send_message(chat_id, message_text, reply_markup=markup)
        return

    if text == "🆘 Помощь":
        bot.send_message(chat_id, "ℹ️ Чтобы начать разговор, просто напишите, что у вас на душе. Я отвечу и постараюсь помочь 💬", reply_markup=main_menu())
        return

    if text == "ℹ️ О нас":
        bot.send_message(chat_id, "Я — Ила, ваш ИИ-собеседник. Готова поддержать в трудную минуту.", reply_markup=main_menu())
        return

    if text == "📜 Условия пользования":
        bot.send_message(chat_id, "Полные условия можно посмотреть на сайте: [ссылка]", reply_markup=main_menu())
        return

    if text == "🔁 Сбросить диалог":
        reset_user_thread(db, user)
        bot.send_message(chat_id, "♻️ Диалог сброшен. Можешь начать новый разговор, и я забуду всё, что было сказано ранее.", reply_markup=main_menu())
        return

    if text in ["💳 Купить подписку", "🗓 Купить на 1 месяц", "📅 Купить на 1 год"]:
        bot.send_message(chat_id, "Выберите срок подписки:", reply_markup=subscription_plan_keyboard())
        return

    # Если ни одно из меню не подошло — считается обычным сообщением
    if contains_crisis_words(text):
        log_crisis_message(user, text)

    try:
        assistant_response, thread_id = send_message_to_assistant(user.thread_id, text)
        user.thread_id = thread_id
        increment_message_count(db, user)
        assistant_response = clean_markdown(assistant_response)
        bot.send_message(chat_id, assistant_response, reply_markup=main_menu())
    except Exception as e:
        bot.send_message(chat_id, "⚠️ Произошла ошибка при обращении к ИИ. Попробуйте позже.")

