from aiogram import Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import random

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

    # остальные темы (тревога обрабатывается отдельно)
    if topic == "topic_relationships":
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


# ---------- КНОПКИ ДЛЯ ТРЕВОГИ ----------
anxiety_options = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🔹 Да, давай", callback_data="anxiety_yes"),
        InlineKeyboardButton(text="🔹 Просто хочу поговорить", callback_data="anxiety_talk")
    ]
])

anxiety_breathing = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="💫 Да, стало легче", callback_data="anxiety_relax_done"),
        InlineKeyboardButton(text="🔁 Нет, сделать ещё раз", callback_data="anxiety_repeat")
    ]
])


# ---------- ТРЕВОГА И БЕСПОКОЙСТВО ----------
@router.callback_query(F.data == "topic_anxiety")
async def handle_anxiety(callback: CallbackQuery):
    await callback.message.answer(
        "Иногда тревога просто хочет, чтобы её услышали 🌿\n"
        "Хочешь, я помогу тебе немного успокоиться?",
        reply_markup=anxiety_options
    )
    await callback.answer()


# ---------- "ДА, ДАВАЙ" (дыхательная техника) ----------
@router.callback_query(F.data == "anxiety_yes")
async def handle_anxiety_yes(callback: CallbackQuery):
    await callback.message.answer(
        "🌬 Хорошо.\n"
        "Вот простая техника дыхания, которая помогает немного отпустить напряжение:\n\n"
        "1️⃣ Сделай глубокий вдох через нос на 4 счёта.\n"
        "2️⃣ Задержи дыхание на 2 секунды.\n"
        "3️⃣ Медленно выдохни через рот на 6 счётов.\n\n"
        "Повтори так 3 раза 🌿\n\n"
        "💫 Когда закончишь, нажми ниже:",
        reply_markup=anxiety_breathing
    )
    await callback.answer()


# ---------- "ДА, СТАЛО ЛЕГЧЕ" ----------
@router.callback_query(F.data == "anxiety_relax_done")
async def handle_anxiety_relax_done(callback: CallbackQuery):
    responses = [
        "🌿 Рад(а), что тебе стало чуть спокойнее. Иногда достаточно просто немного замедлиться.\n\nЕсли чувствуешь, что хочешь продолжить — я рядом.",
        "💫 Отлично. Даже несколько осознанных вдохов уже делают день легче.\n\nХочешь, немного поговорим о том, как сохранять это состояние дольше?",
        "🌬 Хорошо. Иногда достаточно напомнить себе: *я здесь, и со мной всё в порядке.*\n\nЕсли хочешь — можем продолжить разговор.",
        "🌿 Замечательно. Пусть внутри останется немного этого спокойствия.\n\nЕсли считаешь нужным, давай продолжим нашу терапию или просто побудем в диалоге."
    ]
    text = random.choice(responses)
    await callback.message.answer(text)
    await callback.answer()


# ---------- "НЕТ, СДЕЛАТЬ ЕЩЁ РАЗ" ----------
@router.callback_query(F.data == "anxiety_repeat")
async def handle_anxiety_repeat(callback: CallbackQuery):
    await callback.message.answer(
        "Хорошо 🌬\n"
        "Повтори технику ещё раз:\n\n"
        "Вдох — 4 счёта,\n"
        "Пауза — 2,\n"
        "Выдох — 6 🌿\n\n"
        "💫 Когда почувствуешь — нажми “Да, стало легче”.",
        reply_markup=anxiety_breathing
    )
    await callback.answer()


# ---------- "ПРОСТО ХОЧУ ПОГОВОРИТЬ" ----------
@router.callback_query(F.data == "anxiety_talk")
async def handle_anxiety_talk(callback: CallbackQuery):
    await callback.message.answer(
        "Конечно 🌿\n"
        "Иногда важно просто немного побыть в разговоре, где можно быть собой.\n\n"
        "О чём бы тебе хотелось сегодня поговорить — может, о чём-то тёплом и настоящем?"
    )
    await callback.answer()
