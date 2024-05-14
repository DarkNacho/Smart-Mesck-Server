from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()


DB_FILE = os.getenv("DB_FILE")
DB_URL = f"sqlite:///{DB_FILE}"

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


if __name__ == "__main__":
    from models import User, SensorData
    from passlib.context import CryptContext

    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    create_database()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    user_nacho = User(
        email="dark_nacho_xd@hotmail.cl",
        id="1",
        phone_number="+56912345678",
        name="Ignacio Martínez",
        rut="198625388",
        validate=True,
        hash_password=bcrypt_context.hash("nacho"),
        role="Practitioner",
    )

    user_admin = User(
        id="231",
        name="Administrador",
        role="Admin",
        hash_password=bcrypt_context.hash("admin"),
        rut="12",
        phone_number="+53",
        validate=True,
        email="dasd@dd.com",
    )

    user_practitioner = User(
        id="204",
        name="practicante prueba",
        role="Practitioner",
        hash_password=bcrypt_context.hash("practitioner"),
        rut="12552",
        phone_number="+51313",
        validate=True,
        email="dasdd@d31d.com",
    )

    user_patient = User(
        id="3",
        role="Patient",
        name="Paciente prueba",
        hash_password=bcrypt_context.hash("patient"),
        rut="1231252",
        phone_number="+5111313",
        validate=True,
        email="patient@nacho.cl",
    )

    session.add(user_nacho)
    session.add(user_admin)
    session.add(user_practitioner)
    session.add(user_patient)

    session.commit()
