from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import Annotated
from sqlmodel import Session
from database import get_session
from starlette import status
from jose import jwt, JWTError

from models import User
from emailService import send_email

SECRET_KEY = "14dadd1cbcaf8c19db3666aa5c172f0a4d22d17e8f4a34069d74e987b719e4a0"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


router = APIRouter(prefix="/auth", tags=["auth"])
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/auth/token")

class CreateUser(BaseModel):
    email: str
    password: str
    rut: str
    phone_number: str
     
class Token(BaseModel):
    access_token: str
    token_type: str
    
db_dependency = Annotated[Session, Depends(get_session)]

@router.post("/register",status_code=status.HTTP_201_CREATED)
async def register(user: CreateUser, db: db_dependency):
    user = User(email=user.email, hash_password=bcrypt_context.hash(user.password), rut=user.rut, phone_number=user.phone_number)
    db.add(user)
    db.commit()
    db.refresh(user)
    token = generate_email_confirmation_token(user)
    send_email([user.email], "Confirm your email", f"Click here to confirm your email: http://localhost:8000/auth/activate/{token}")
    
@router.post("/token", response_model=Token)
async def login(db: db_dependency, form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        return {"error": "Invalid credentials"}
    if not bcrypt_context.verify(form_data.password, user.hash_password):
        return {"error": "Invalid credentials"}
    return {"access_token": create_access_token(user), "token_type": "bearer"}


def create_access_token(user: User):
    payload = {"sub": user.email, "id": user.id, "exp": datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def generate_email_confirmation_token(user: User, ):
    payload = {"sub": user.email, "id": user.id, "exp": datetime.now() + timedelta(days=3)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@router.get("/activate/{token}")
async def activate_user(token: str, db: db_dependency):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("id")
        user : User = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "Invalid token"}
        user.validate = True
        db.commit()
        return {"message": "User activated successfully"}
    except JWTError:
        return {"error": "Invalid token"}