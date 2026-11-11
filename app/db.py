import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Адрес базы с паролем берем из файла .env
load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/subscriptions"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


# Открываем соединение с базой на один запрос и потом закрываем
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
