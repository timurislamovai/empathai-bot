import psycopg2
import os

# 📌 Вставь сюда свои данные из Render → Connection
DB_NAME = "empathai_db_5rz1"
DB_USER = "empathai_db_5rz1_user"
DB_PASSWORD = "sEEqC2E49tl7qBbMaqlIwcjGlnQaRZ6N"
DB_HOST = "dpg-d186908gjchc73dqolo0-a"
DB_PORT = "5432"

connection = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)

cursor = connection.cursor()

try:
    cursor.execute("ALTER TABLE users ADD COLUMN first_seen_at TIMESTAMP DEFAULT NOW();")
    cursor.execute("ALTER TABLE users ADD COLUMN last_message_at TIMESTAMP DEFAULT NOW();")
    cursor.execute("ALTER TABLE users ADD COLUMN total_messages INTEGER DEFAULT 0;")
    connection.commit()
    print("✅ Все поля успешно добавлены в таблицу users.")
except Exception as e:
    print("❌ Ошибка:", e)

cursor.close()
connection.close()
