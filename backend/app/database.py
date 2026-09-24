import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Получаем URL из переменных окружения (или используем значение по умолчанию для Docker)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/tabel")

# Создаем engine (движок подключения к БД)
engine = create_engine(DATABASE_URL)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для всех моделей (SQLAlchemy 2.0)
class Base(DeclarativeBase):
    pass

# Зависимость для получения сессии БД в эндпоинтах
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()