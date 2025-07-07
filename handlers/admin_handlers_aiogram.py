from aiogram import types
from aiogram.filters import Command
from sqlalchemy import func
from bot_instance import dp
from database import SessionLocal
from models import get_user_by_telegram_id, create_user, User

ADMIN_IDS = ["944583273", "396497806"]

# 📊 /admin_stats — статистика
@dp.message(Command("admin_stats"))
async def admin_stats(message: types.Message):
    telegram_id = str(message.from_user.id)
    if telegram_id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    db = SessionLocal()
    total_users = db.query(User).count()
    paid_users = db.query(User).filter(User.has_paid == True).count()
    unlimited_users = db.query(User).filter(User.is_unlimited == True).count()

    await message.answer(
        f"📊 Общая статистика:\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"💳 С подпиской: {paid_users}\n"
        f"♾ Безлимит: {unlimited_users}"
    )

# 🤝 /admin_referrals — топ-рефералы
@dp.message(Command("admin_referrals"))
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
@dp.message(Command("give_unlimited"))
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
