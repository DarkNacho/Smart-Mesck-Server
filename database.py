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


def create_admin_user(
    rut, name, password, email, phone_number, fhir_id=None, secondary_roles=None
):
    """
    Creates an admin user in the database.

    Args:
        rut: User's RUT (Chilean ID)
        name: User's full name
        password: Plain text password (will be hashed)
        email: User's email
        phone_number: User's phone number
        fhir_id: Optional FHIR ID
        secondary_roles: Optional comma-separated secondary roles

    Returns:
        The created User object
    """
    from models import User
    from passlib.context import CryptContext

    # Create password context for hashing
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        # Check if user with this RUT already exists
        existing_user = session.query(User).filter(User.rut == rut).first()
        if existing_user:
            print(f"User with RUT {rut} already exists")
            return existing_user

        # Create new user
        new_user = User(
            rut=rut,
            name=name,
            hash_password=pwd_context.hash(password),
            role="Admin",
            secondaryRoles=secondary_roles,
            email=email,
            phone_number=phone_number,
            fhir_id=fhir_id,
            validate=True,  # Admin users are validated by default
        )

        # Add to database
        session.add(new_user)
        session.commit()
        session.refresh(new_user)

        print(f"Admin user '{name}' created successfully")
        return new_user

    except Exception as e:
        session.rollback()
        print(f"Error creating admin user: {e}")
        raise
    finally:
        session.close()


# just create the database and tables
if __name__ == "__main__":
    from models import GameData
    from passlib.context import CryptContext

    create_database()
