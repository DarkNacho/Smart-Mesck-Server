from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()


DB_FILE = os.getenv("DB_FILE")
DB_URL =  f"sqlite:///{DB_FILE}"

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

    create_database()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    user_nacho = User(email="dark_nacho_xd@hotmail.cl",
                      id="4", phone_number="+56912345678", 
                      rut="198625388", validate=True,
                      hash_password=bcrypt_context.hash("nacho12345"),
                      role="Patient")
    
    user_admin = User(id="231", role="Admin", hash_password=bcrypt_context.hash("admin"), rut="12", phone_number="+53", validate=True, email="dasd@dd.com")
    
    
    user_practitioner = User(id="204", role="Practitioner",
                             hash_password=bcrypt_context.hash("practitioner"), 
                             rut="12552", phone_number="+51313", 
                             validate=True, 
                             email="dasdd@d31d.com")
    
    session.add(user_nacho)
    session.add(user_admin)
    session.add(user_practitioner)
    
    session.commit()