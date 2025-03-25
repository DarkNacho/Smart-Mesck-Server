from datetime import datetime
import random
from sqlmodel import SQLModel, create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()


DB_URL = os.getenv("DB_URL")
# DB_FILE = "sqlite:///database.db"
engine = create_engine(DB_URL, echo=True)


def create_database():
    SQLModel.metadata.create_all(engine)


def get_session():
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# just create the database and tables
if __name__ == "__main__":
    from models import GameData
    from passlib.context import CryptContext

    create_database()
