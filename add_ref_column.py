from sqlalchemy import create_engine, text
import os

engine = create_engine(os.getenv("DATABASE_URL"))

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS referrer_code TEXT;"))
    print("✅ Колонка referrer_code добавлена.")
