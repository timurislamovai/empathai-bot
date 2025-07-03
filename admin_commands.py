# admin_commands.py

from models import User, get_user_by_telegram_id, create_user
from telegram import Bot
from sqlalchemy.orm import Session

# ✅ /admin_stats — общая статистика
def handle_admin_stats(db: Session, chat_id: int, bot: Bot):
    total_users = db.query(User).count()
    paid_users = db.query(User).filter(User.has_paid == True).count()
    unlimited_users = db.query(User).filter(User.is_unlimited == True).count()

    bot.send_message(
        chat_id,
        f"📊 Общая статистика:\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"💳 С подпиской: {paid_users}\n"
        f"♾ Безлимит: {unlimited_users}"
    )

# ✅ /admin_referrals — ТОП пригласивших
def handle_admin_referrals(db: Session, chat_id: int, bot: Bot):
    from sqlalchemy import func

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

    message = "📊 Реферальная статистика (ТОП 10):\n"
    for i, (ref_code, count) in enumerate(top_referrers, start=1):
        message += f"{i}. {ref_code} — {count} приглашённых\n"

    message += f"\n🔢 Всего приглашённых: {total_referrals}"
    message += f"\n💸 Уникальных рефереров: {unique_referrers}"

    bot.send_message(chat_id, message)

# ✅ /give_unlimited <id> — выдать безлимит
def give_unlimited_access(db: Session, bot: Bot, chat_id: int, text: str):
    parts = text.strip().split()
    if len(parts) != 2:
        bot.send_message(chat_id, "⚠️ Использование: /give_unlimited <telegram_id>")
        return

    target_id = parts[1]
    target_user = get_user_by_telegram_id(db, target_id)
    if not target_user:
        target_user = create_user(db, target_id)

    target_user.is_unlimited = True
    db.commit()

    bot.send_message(chat_id, f"✅ Пользователю {target_id} выдан безлимитный доступ.")
