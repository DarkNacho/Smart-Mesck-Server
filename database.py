from sqlmodel import SQLModel, create_engine
from sqlalchemy.orm import sessionmaker


DB_FILE = "database.db"
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
    create_database()