from fastapi import APIRouter, Depends
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from fastapi import HTTPException
from pydantic import BaseModel
import os

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
class AdminLogin(BaseModel):
    username: str
    password: str

class Settings(BaseModel):
    authjwt_secret_key: str = os.getenv("ADMIN_JWT_SECRET", "supersecret")

@AuthJWT.load_config
def get_config():
    return Settings()

@router.post("/login")
def login(data: AdminLogin, Authorize: AuthJWT = Depends()):
    if data.username != "admin" or data.password != os.getenv("ADMIN_PASSWORD", "admin123"):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    access_token = Authorize.create_access_token(subject=data.username)
    return {"access_token": access_token}


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

