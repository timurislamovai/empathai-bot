from models import Base
from database import engine

def init_db():
    print("✅ Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created.")

if __name__ == "__main__":
    init_db()
