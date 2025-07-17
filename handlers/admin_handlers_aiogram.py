from aiogram import types, Router, F
from aiogram.filters import Command
from sqlalchemy import func
from database import SessionLocal
from models import get_user_by_telegram_id, create_user, User
from datetime import datetime
from utils import get_stats_summary
from asyncio import sleep
from datetime import timedelta


router = Router()

MIN_PAYOUT_AMOUNT = 5000  # Минимальная сумма, необходимая для выплаты

ADMIN_IDS = ["944583273", "396497806"]

@router.message(Command("admin_user"))
async def handle_admin_user(message: types.Message):
    if str(message.from_user.id) not in ADMIN_IDS:
        return await message.answer("🚫 У вас нет доступа к этой команде.")

    parts = message.text.strip().split()
    if len(parts) < 2:
        return await message.answer("❗ Используйте: /admin_user <telegram_id>")

    telegram_id = parts[1].strip()

    db = SessionLocal()
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return await message.answer("❌ Пользователь не найден.")

    # 👥 Подсчёт приглашённых
    invited_count = db.query(User).filter(User.referrer_code == str(telegram_id)).count()

    earned = round(user.referral_earned or 0.0, 2)
    paid = round(user.referral_paid or 0.0, 2)
    to_pay = round(earned - paid, 2)

    text = (
        f"👤 Пользователь (Telegram ID): {telegram_id}\n\n"
        f"👥 Приглашено: {invited_count} чел.\n"
        f"💸 Заработано: {earned} ₽\n"
        f"💳 Выплачено: {paid} ₽\n"
        f"💰 Остаток к выплате: {to_pay} ₽\n"
    )

    if to_pay >= MIN_PAYOUT_AMOUNT:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(
                text=f"✅ Отметить как выплачено {to_pay} ₽",
                callback_data=f"confirm_payout:{telegram_id}:{to_pay}"
            )]
        ])
        await message.answer(text, reply_markup=keyboard)
    else:
        text += f"\n❌ Недостаточно для выплаты (минимум {MIN_PAYOUT_AMOUNT} ₽)"
        await message.answer(text)





@router.message(Command("admin_stats"))
async def handle_admin_stats(message: types.Message):
    if str(message.from_user.id) not in ADMIN_IDS:
        return await message.answer("🚫 У вас нет доступа к этой команде.")

    try:
        db = SessionLocal()
        stats = get_stats_summary(db)

        print("📊 Ответ статистики:")
        print(stats)
        print(f"📏 Длина: {len(stats)}")

        # Временно обрежем, чтобы Telegram точно принял
        await message.answer(stats[:3000])

    except Exception as e:
        print("❌ Ошибка в /admin_stats:", e)
        await message.answer("⚠️ Ошибка при выводе статистики.")



# 🤝 /admin_referrals — топ-рефералы
@router.message(Command("admin_referrals"))
async def admin_referrals(message: types.Message):
    telegram_id = str(message.from_user.id)
    if telegram_id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    db = SessionLocal()
    top_referrers = (
        db.query(User.referrer_code, func.count(User.id).label("ref_count"))
        .filter(User.referrer_code.isnot(None))
        .group_by(User.referrer_code)
        .order_by(func.count(User.id).desc())
        .limit(10)
        .all()
    )

    total_referrals = db.query(User).filter(User.referrer_code.isnot(None)).count()
    unique_referrers = db.query(User.referrer_code).distinct().count()

    message_text = "📊 Реферальная статистика (ТОП 10):\n"
    for i, (ref_code, count) in enumerate(top_referrers, start=1):
        message_text += f"{i}. {ref_code} — {count} приглашённых\n"

    message_text += f"\n🔢 Всего приглашённых: {total_referrals}"
    message_text += f"\n💸 Уникальных рефереров: {unique_referrers}"

    await message.answer(message_text)

# ♾ /give_unlimited <id> — выдать безлимит
@router.message(Command("give_unlimited"))
async def give_unlimited(message: types.Message):
    telegram_id = str(message.from_user.id)
    if telegram_id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.answer("⚠️ Использование: /give_unlimited <telegram_id>")
        return

    target_id = parts[1]
    db = SessionLocal()
    target_user = get_user_by_telegram_id(db, target_id)

    if not target_user:
        target_user = create_user(db, target_id)

    target_user.is_unlimited = True
    db.commit()

    await message.answer(f"✅ Пользователю {target_id} выдан безлимитный доступ.")


@router.callback_query(F.data.startswith("confirm_payout:"))
async def confirm_referral_payout(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 3:
        return await callback.message.answer("❌ Ошибка: некорректные данные кнопки.")

    telegram_id = parts[1]
    payout_amount = float(parts[2])

    db = SessionLocal()
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return await callback.message.answer("❌ Пользователь не найден.")

    earned = round(user.referral_earned or 0.0, 2)
    paid = round(user.referral_paid or 0.0, 2)
    to_pay = round(earned - paid, 2)

    if payout_amount > to_pay:
        return await callback.message.answer("⚠️ Сумма выплаты превышает доступный остаток.")

    user.referral_paid = paid + payout_amount
    db.commit()

    new_balance = round(earned - user.referral_paid, 2)
    username_display = getattr(user, "username", "неизвестен")

    await callback.message.answer(
        f"✅ Выплата {payout_amount} ₽ пользователю @{username_display} отмечена.\n"
        f"Новый остаток: {new_balance} ₽"
    )

    await callback.answer()



@router.message(Command("delete_user"))
async def delete_user_handler(message: types.Message):
    db = SessionLocal()

    # Проверка доступа
    if str(message.from_user.id) not in ADMIN_IDS:
        return await message.answer("❌ У вас нет доступа к этой команде.")

    args = message.text.strip().split()
    if len(args) != 2 or not args[1].isdigit():
        return await message.answer("⚠ Укажите Telegram ID: /delete_user 123456789")

    telegram_id = args[1]
    user = get_user_by_telegram_id(db, telegram_id)

    if not user:
        return await message.answer("❌ Пользователь не найден.")

    # Удаление из базы
    db.delete(user)
    db.commit()

    # Запись в лог
    log_entry = f"[{datetime.utcnow()}] 🗑 Удалён пользователь {telegram_id} админом {message.from_user.id}\n"
    with open("deleted_users.log", "a", encoding="utf-8") as f:
        f.write(log_entry)

    await message.answer(f"✅ Пользователь с ID {telegram_id} удалён из базы.")



@router.message(Command("admin_ping_inactive"))
async def handle_admin_ping_inactive(message: types.Message):
    if str(message.from_user.id) not in ADMIN_IDS:
        return await message.answer("🚫 У вас нет доступа к этой команде.")

    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("❗ Используйте: /admin_ping_inactive <текст сообщения>")

    text_to_send = parts[1].strip()

    db = SessionLocal()
    two_days_ago = datetime.utcnow() - timedelta(days=2)
    users = db.query(User).filter(User.last_message_at < two_days_ago).all()

    if not users:
        return await message.answer("👥 Нет пользователей, не писавших более 2 дней.")

    count_sent = 0
    for user in users:
        try:
            await message.bot.send_message(chat_id=int(user.telegram_id), text=text_to_send)
            count_sent += 1
            await sleep(0.5)  # пауза между отправками
        except Exception as e:
            print(f"❌ Не удалось отправить {user.telegram_id}: {e}")
            continue

    await message.answer(f"✅ Сообщение отправлено {count_sent} пользователям.")
