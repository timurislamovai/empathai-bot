from models import Base
from database import engine

def reset_db():
    print("⚠️ Удаляем все таблицы...")
    Base.metadata.drop_all(bind=engine)

    print("✅ Создаём заново таблицы...")
    Base.metadata.create_all(bind=engine)

    print("✅ Таблицы успешно пересозданы.")

if __name__ == "__main__":
    reset_db()
