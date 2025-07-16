from models import Base
from database import engine
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

def init_db():
    print("✅ Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created.")
    ensure_column_exists()

def ensure_column_exists():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN free_message_limit INTEGER DEFAULT 50;"))
            print("✅ Колонка free_message_limit добавлена в таблицу users.")
        except ProgrammingError as e:
            if 'already exists' in str(e):
                print("ℹ️ Колонка уже существует — пропускаем.")
            else:
                print("❌ Ошибка при добавлении колонки:")
                raise

if __name__ == "__main__":
    init_db()
