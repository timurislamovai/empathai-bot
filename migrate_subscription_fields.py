import os
from sqlalchemy import create_engine
from sqlalchemy import text


DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL)

with engine.connect() as connection:
    connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS has_paid BOOLEAN DEFAULT FALSE;"))
    connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMP;"))

print("✅ Поля подписки добавлены в таблицу users")
