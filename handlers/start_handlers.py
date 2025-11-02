from aiogram import Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

router = Router()

# ---------- КНОПКИ ТЕМ ----------
def topics_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌫 Тревога и беспокойство", callback_data="topic_anxiety")],
        [InlineKeyboardButton(text="💔 Отношения и чувства", callback_data="topic_relationships")],
        [InlineKeyboardButton(text="🌱 Самооценка и уверенность", callback_data="topic_selfesteem")],
        [InlineKeyboardButton(text="😴 Усталость и выгорание", callback_data="topic_burnout")],
        [InlineKeyboardButton(text="✨ Просто хочу поговорить", callback_data="topic_chat")],
    ])
    return keyboard


# ---------- ОБРАБОТЧИК ВЫБОРА ТЕМ ----------
@router.callback_query(F.data.startswith("topic_"))
async def handle_topic_selection(callback: CallbackQuery):
    topic = callback.data

    if topic == "topic_anxiety":
        await callback.message.answer(
            "Иногда тревога просто хочет, чтобы её услышали 🌿\n"
            "Хочешь, я помогу тебе немного успокоиться?\n\n"
            "🔹 Да, давай\n🔹 Просто хочу поговорить"
        )

    elif topic == "topic_relationships":
        await callback.message.answer(
            "Отношения — это важно 💛\n"
            "Хочешь рассказать, что происходит, или просто обсудить, что чувствуешь?\n\n"
            "🔹 Хочу рассказать\n🔹 Просто обсудить"
        )

    elif topic == "topic_selfesteem":
        await callback.message.answer(
            "Бывает, уверенность теряется даже у самых сильных 🌱\n"
            "Хочешь немного поддержки или упражнения для самооценки?"
        )

    elif topic == "topic_burnout":
        await callback.message.answer(
            "Ты, похоже, очень устал 😞\n"
            "Давай попробуем немного разгрузить голову и дыхание, хорошо?"
        )

    elif topic == "topic_chat":
        await callback.message.answer(
            "Я рядом 🌿 Просто напиши, что чувствуешь. Я слушаю."
        )

    await callback.answer()  # закрываем "часики" у кнопки
