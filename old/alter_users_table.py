from database import engine
from sqlalchemy import text

with engine.connect() as connection:
    connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS referrer_code TEXT;"))
    print("✅ Колонка referrer_code добавлена (если её не было).")
