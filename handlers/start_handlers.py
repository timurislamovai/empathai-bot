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
@router.callback_query(
    F.data.startswith("topic_")
    & (F.data != "topic_anxiety")
    & (F.data != "topic_relationships")
    & (F.data != "topic_selfesteem")
)
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
    [InlineKeyboardButton(text="🔹 Да, давай", callback_data="anxiety_yes")],
    [InlineKeyboardButton(text="🔹 Просто хочу поговорить", callback_data="anxiety_talk")]
])

anxiety_breathing = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💫 Да, стало легче", callback_data="anxiety_relax_done")],
    [InlineKeyboardButton(text="🔁 Нет, сделать ещё раз", callback_data="anxiety_repeat")]
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

# ---------- ОТНОШЕНИЯ И ЧУВСТВА ----------

# Кнопки выбора подкатегорий
relationships_options = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💔 Мне тяжело доверять", callback_data="rel_trust")],
    [InlineKeyboardButton(text="🌫 Кажется, мы отдалились", callback_data="rel_distance")],
    [InlineKeyboardButton(text="🌱 Хочу понять, что я чувствую", callback_data="rel_understand")],
    [InlineKeyboardButton(text="💞 Хочу вернуть тепло между нами", callback_data="rel_warmth")],
    [InlineKeyboardButton(text="💬 Просто хочу поговорить", callback_data="rel_talk")]
])


# ---------- ПЕРВИЧНЫЙ ВХОД В ТЕМУ ----------
@router.callback_query(F.data == "topic_relationships")
async def handle_relationships(callback: CallbackQuery):
    await callback.message.answer(
        "Отношения — это важно 💛\n"
        "Иногда в них бывает непросто — даже когда всё вроде спокойно.\n\n"
        "Хочешь, я помогу тебе немного разобраться в своих чувствах?",
        reply_markup=relationships_options
    )
    await callback.answer()


# ---------- 💔 Мне тяжело доверять ----------
@router.callback_query(F.data == "rel_trust")
async def handle_rel_trust(callback: CallbackQuery):
    await callback.message.answer(
        "Это непросто — снова открыться, когда доверие было ранено 💔\n\n"
        "Просто знай, что ты не один(а).\n"
        "Иногда путь к доверию начинается с разрешения себе чувствовать боль без вины.\n\n"
        "Можешь рассказать, что сейчас помогает тебе держаться?"
    )
    await callback.answer()


# ---------- 🌫 Кажется, мы отдалились ----------
@router.callback_query(F.data == "rel_distance")
async def handle_rel_distance(callback: CallbackQuery):
    await callback.message.answer(
        "Бывает, что тишина между людьми становится громче слов 🌫\n\n"
        "Это не всегда конец — иногда это просто пауза, чтобы услышать себя и друг друга.\n\n"
        "Можешь рассказать, что чувствуешь сейчас?"
    )
    await callback.answer()


# ---------- 🌱 Хочу понять, что я чувствую ----------
@router.callback_query(F.data == "rel_understand")
async def handle_rel_understand(callback: CallbackQuery):
    await callback.message.answer(
        "Это уже шаг к осознанности 🌱\n\n"
        "Не нужно торопиться с ответом — просто попробуй описать, какие эмоции ближе всего к тебе в этот момент."
    )
    await callback.answer()


# ---------- 💞 Хочу вернуть тепло между нами ----------
@router.callback_query(F.data == "rel_warmth")
async def handle_rel_warmth(callback: CallbackQuery):
    await callback.message.answer(
        "Это тёплое и живое желание 💞\n\n"
        "Любовь не исчезает — иногда ей просто нужно немного внимания и слов.\n\n"
        "Можешь рассказать, что для тебя значит «тепло» в отношениях?"
    )
    await callback.answer()


# ---------- 💬 Просто хочу поговорить ----------
@router.callback_query(F.data == "rel_talk")
async def handle_rel_talk(callback: CallbackQuery):
    await callback.message.answer(
        "Конечно 🌿\n"
        "Иногда не нужно искать смысл — просто быть в разговоре уже достаточно.\n\n"
        "Я рядом. Пиши так, как чувствуешь."
    )
    await callback.answer()

# ---------- САМООЦЕНКА И УВЕРЕННОСТЬ ----------

# Кнопки подкатегорий
selfesteem_options = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💭 Мне сложно себя принять", callback_data="esteem_accept")],
    [InlineKeyboardButton(text="💫 Хочу чувствовать уверенность", callback_data="esteem_confident")],
    [InlineKeyboardButton(text="🌸 Я часто сравниваю себя с другими", callback_data="esteem_compare")],
    [InlineKeyboardButton(text="💬 Просто хочу поговорить", callback_data="esteem_talk")]
])


# ---------- ПЕРВИЧНЫЙ ВХОД В ТЕМУ ----------
@router.callback_query(F.data == "topic_selfesteem")
async def handle_selfesteem(callback: CallbackQuery):
    await callback.message.answer(
        "Уверенность не появляется мгновенно 🌿\n"
        "Она растёт, когда мы начинаем относиться к себе с добротой, а не с критикой.\n\n"
        "Что тебе ближе сейчас?",
        reply_markup=selfesteem_options
    )
    await callback.answer()


# ---------- 💭 Мне сложно себя принять ----------
@router.callback_query(F.data == "esteem_accept")
async def handle_esteem_accept(callback: CallbackQuery):
    await callback.message.answer(
        "Это чувство знакомо многим 💛\n"
        "Иногда мы видим в себе только недостатки,\n"
        "забывая, что даже в уязвимости есть сила.\n\n"
        "Хочешь рассказать, в чём тебе сейчас сложнее всего быть добрым к себе?"
    )
    await callback.answer()


# ---------- 💫 Хочу чувствовать уверенность ----------
@router.callback_query(F.data == "esteem_confident")
async def handle_esteem_confident(callback: CallbackQuery):
    await callback.message.answer(
        "Это хорошее и очень честное желание 🌿\n"
        "Уверенность не всегда громкая —\n"
        "иногда это просто внутреннее *«я справлюсь»*, даже если немного страшно.\n\n"
        "Что помогает тебе чувствовать себя сильнее, хоть немного?"
    )
    await callback.answer()


# ---------- 🌸 Я часто сравниваю себя с другими ----------
@router.callback_query(F.data == "esteem_compare")
async def handle_esteem_compare(callback: CallbackQuery):
    await callback.message.answer(
        "Сравнение — ловушка, в которую мы все попадаем 🌸\n\n"
        "Попробуй не бороться с этим, а просто заметить: у тебя свой ритм, своя дорога.\n\n"
        "Можешь рассказать, в какие моменты тебе труднее всего не сравнивать?"
    )
    await callback.answer()


# ---------- 💬 Просто хочу поговорить ----------
@router.callback_query(F.data == "esteem_talk")
async def handle_esteem_talk(callback: CallbackQuery):
    await callback.message.answer(
        "Конечно 🌿\n"
        "Иногда не нужно искать ответы — просто немного тепла и присутствия уже достаточно.\n\n"
        "Я рядом, можешь написать, что чувствуешь прямо сейчас."
    )
    await callback.answer()
