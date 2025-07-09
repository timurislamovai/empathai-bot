from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["admin"])

# Получение подключения к БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total_users = db.query(User).count()
    paid_users = db.query(User).filter(User.has_paid == True).count()
    trial_users = db.query(User).filter(
        User.has_paid == False,
        User.subscription_expires_at != None
    ).count()
    expired_users = db.query(User).filter(
        User.subscription_expires_at != None,
        User.subscription_expires_at < datetime.utcnow()
    ).count()

    return {
        "total": total_users,
        "paid": paid_users,
        "trial": trial_users,
        "expired": expired_users
    }

