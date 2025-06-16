from db import Base, engine
from models import User

# Создаём таблицы в базе данных
Base.metadata.create_all(bind=engine)

print("✅ Таблицы успешно созданы.")
