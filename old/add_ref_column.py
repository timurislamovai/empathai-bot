from sqlalchemy import create_engine, text
import os

engine = create_engine(os.getenv("DATABASE_URL"))

check_column_sql = """
SELECT column_name 
FROM information_schema.columns 
WHERE table_name='users' AND column_name='referrer_code';
"""

add_column_sql = "ALTER TABLE users ADD COLUMN referrer_code TEXT;"

with engine.connect() as conn:
    result = conn.execute(text(check_column_sql))
    column_exists = result.first()
    if column_exists:
        print("ℹ️ Колонка referrer_code уже существует.")
    else:
        conn.execute(text(add_column_sql))
        print("✅ Колонка referrer_code добавлена.")
