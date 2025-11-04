# handlers/evening_handlers_aiogram.py
import datetime
import json
import asyncio 
import random
from pathlib import Path
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from database import SessionLocal
from models import EveningRitualLog
from utils import is_user_premium

router = Router()

QUESTIONS_PATH = Path("data/evening_questions.json")
NOTE_MAX_LEN = 80
CB_FINISH_DAY = "finish_day"
CB_EMOTION_PREFIX = "emotion:"
CB_WRITE_NOTE = "write_note"

EMOTION_MAP = {
    "calm": {"label": "🌿 Спокойствие", "reply": "Тихо и светло внутри — пусть ночь сохранит этот покой."},
    "joy": {"label": "☀️ Радость", "reply": "Как чудесно — пусть радость будет твоим утренним светом."},
    "tired": {"label": "😴 Усталость", "reply": "Ты устал(а). Теперь можно отдыхать — просто будь."},
    "tension": {"label": "🔥 Напряжение", "reply": "Ты сделал(а) всё, что мог(ла). Выдохни и отпусти."},
    "sad": {"label": "🌧️ Грусть", "reply": "Грусть — это часть. Ночь обнимет и исцелит."},
}


class EveningState(StatesGroup):
    waiting_for_note = State()


def invitation_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Завершить день", callback_data=CB_FINISH_DAY)]
    ])


def question_keyboard():
    buttons = [
        InlineKeyboardButton(text=EMOTION_MAP["calm"]["label"], callback_data=f"{CB_EMOTION_PREFIX}calm"),
        InlineKeyboardButton(text=EMOTION_MAP["joy"]["label"], callback_data=f"{CB_EMOTION_PREFIX}joy"),
        InlineKeyboardButton(text=EMOTION_MAP["tired"]["label"], callback_data=f"{CB_EMOTION_PREFIX}tired"),
        InlineKeyboardButton(text=EMOTION_MAP["tension"]["label"], callback_data=f"{CB_EMOTION_PREFIX}tension"),
        InlineKeyboardButton(text=EMOTION_MAP["sad"]["label"], callback_data=f"{CB_EMOTION_PREFIX}sad"),
        InlineKeyboardButton(text="✍️ Хочу написать", callback_data=CB_WRITE_NOTE),
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons[i:i + 2] for i in range(0, len(buttons), 2)])


def get_question(is_premium: bool):
    with open(QUESTIONS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    questions = data["premium"] if is_premium else data["free"]
    return random.choice(questions)


# --------- Хэндлеры ---------

# 🌙 Шаг 1 — Первое сообщение “начало ритуала”
@router.message(lambda m: m.text == "/evening_test")
async def test_evening(message: types.Message):
    start_text = (
        "🌙 *День подходит к концу...*\n\n"
        "Ты прожил(а) ещё один день — со своими мыслями, чувствами, моментами.\n"
        "Хочешь подвести маленький итог вместе со мной? 💫"
    )

    await message.answer(
        start_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✨ Завершить день", callback_data=CB_FINISH_DAY)]
        ])
    )


# 🌿 Шаг 2 — Второе сообщение “вопрос вечера + выбор эмоции”
@router.callback_query(lambda c: c.data == CB_FINISH_DAY)
async def start_evening_ritual(query: types.CallbackQuery):
    try:
        user_id = query.from_user.id
        is_premium = is_user_premium(user_id)

        # ✨ Новый текст, наполненный эмоцией
        question_text = (
            "🕯 *Что сегодня было трудно, но ты с этим справился(ась)?*\n\n"
            "_Выбери состояние, которое ближе тебе сейчас —_\n"
            "_или напиши свои мысли, если хочешь выразиться._"
        )

        # 💫 Отправляем новое сообщение (а не редактируем старое)
        await query.message.answer(
            question_text,
            parse_mode="Markdown",
            reply_markup=question_keyboard()
        )

        # Закрываем callback, чтобы Telegram не крутил “часики”
        await query.answer()

    except Exception as e:
        print(f"❌ Ошибка при запуске вечернего ритуала: {e}")



@router.callback_query(lambda c: c.data and c.data.startswith(CB_EMOTION_PREFIX))
async def handle_emotion(query: types.CallbackQuery):
    db = SessionLocal()
    try:
        user_id = query.from_user.id
        emotion_key = query.data.split(":")[1]
        is_premium = is_user_premium(user_id)
        today = datetime.date.today()

        emotion_data = EMOTION_MAP[emotion_key]
        emotion_label = emotion_data["label"]
        reply_text = emotion_data["reply"]

        # 📜 Сохраняем выбор в лог
        new_log = EveningRitualLog(
            user_id=user_id,
            date=today,
            emotion=emotion_key,
            action="emotion_selected",
            is_premium=is_premium
        )
        db.add(new_log)
        db.commit()

        # 🌙 1️⃣ Шаг: эмоциональный отклик
        formatted_reply = (
            f"{emotion_label}\n\n"
            f"_{reply_text}_"
        )
        await query.message.edit_text(formatted_reply, parse_mode="Markdown")
        await query.answer()

        # ⏳ Пауза — дыхание
        await asyncio.sleep(1.8)

        # 💭 2️⃣ Шаг: мягкое заключение
        closing_lines = [
            "💭 *Сегодня достаточно.*\n_Завтра подарит тебе новые силы._",
            "🌘 *Ты сделал(а) всё, что нужно.*\n_Остальное — для утра._",
            "🌙 *Сегодня — точка.*\n_Завтра — новое дыхание._"
        ]
        closing_text = random.choice(closing_lines)
        await query.message.answer(closing_text, parse_mode="Markdown")

        # ⏳ Ещё немного тишины
        await asyncio.sleep(1.5)

        # 🌔 3️⃣ Шаг: финальное послание — разное для Premium и Free
        if is_premium:
            final_text = (
                "✨ *Ты сделал(а) шаг к осознанности.*\n"
                "_Пусть ночь будет лёгкой и доброй._\n\n"
                "Я рядом, когда захочешь поговорить снова 💫"
            )
        else:
            final_text = (
                "🌌 *Спасибо, что завершил день осознанно.*\n"
                "_Пусть ночь принесёт тебе покой и тишину._\n\n"
                "Возвращайся завтра — я буду рядом 💙"
            )

        await query.message.answer(final_text, parse_mode="Markdown")

    except Exception as e:
        print(f"❌ Ошибка при обработке эмоции: {e}")
    finally:
        db.close()


@router.callback_query(lambda c: c.data == CB_WRITE_NOTE)
async def handle_write_note(query: types.CallbackQuery, state: FSMContext):
    db = SessionLocal()
    try:
        user_id = query.from_user.id
        is_premium = is_user_premium(user_id)
        today = datetime.date.today()

        new_log = EveningRitualLog(
            user_id=user_id,
            date=today,
            emotion=None,
            action="wrote_note",
            is_premium=is_premium
        )
        db.add(new_log)
        db.commit()

        await query.message.edit_text("Опиши свой день в одном предложении (до 80 символов).")
        await state.set_state(EveningState.waiting_for_note)
        await query.answer()
    finally:
        db.close()


@router.message(EveningState.waiting_for_note)
async def handle_note_input(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if len(text) > NOTE_MAX_LEN:
        await message.reply("Попробуй короче. Пусть мысль будет как вдох — короткая, но точная.")
        return

    await message.reply(
        "Спасибо, что поделился. Иногда одно слово несёт целый день в себе.\n\nСегодня достаточно. Завтра — новая возможность."
    )
    await state.clear()
