from datetime import timedelta
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from typing import Annotated
from sqlmodel import Session
from database import get_session
from starlette import status
from jose import ExpiredSignatureError, jwt, JWTError

from models import User, Token
from emailService import send_email
import random
import string
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))


router = APIRouter(prefix="/auth", tags=["auth"])
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/auth/token")
    
db_dependency = Annotated[Session, Depends(get_session)]

@router.post("/register",status_code=status.HTTP_201_CREATED)
async def register(user: User, db: db_dependency):
    if(user.hash_password == None):
        newUser = User(id =user.id, email=user.email, 
                       hash_password=bcrypt_context.hash(generate_random_password()), 
                       rut=user.rut, 
                       phone_number=user.phone_number, 
                       role=user.role)
        
    else:
        newUser = User(id=user.id,email=user.email, 
                       hash_password=bcrypt_context.hash(user.hash_password), 
                       rut=user.rut, 
                       phone_number=user.phone_number, 
                       role=user.role)
        
    db.add(newUser)
    db.commit()
    db.refresh(newUser)
    token = generate_restart_token(newUser)
    send_email([newUser.email], "Confirm your email", f"Click here to confirm your email: http://localhost:8000/auth/activate/{token}")
    
@router.post("/token", response_model=Token)
async def login(db: db_dependency, form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        return {"error": "Invalid credentials"}
    if not bcrypt_context.verify(form_data.password, user.hash_password):
        return {"error": "Invalid credentials"}
    return {"access_token": create_access_token(user), "token_type": "bearer"}

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
    
    
@router.post("/reset-password-token")
async def create_reset_password_token(email: str, db: db_dependency):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"error": "User not found"}
    
    token = generate_restart_token(user)
    send_email([user.email], "Reset Password", f"Click here to reset your password: http://localhost:8000/auth/reset-password/{token}")
    
    return {"message": "Reset password token created successfully"}

@router.post("/reset-password/{token}")
async def reset_password(token: str, new_password: str, db: db_dependency):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("id")
        user : User = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "Invalid token"}
        user.hash_password = bcrypt_context.hash(new_password)
        db.commit()
        return {"message": "Password reset successfully"}
    except JWTError:
        return {"error": "Invalid token"}

        
@router.get("/users/me")        
async def get_current_user(token: str = Depends(oauth2_bearer)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        user_id: str = payload.get("id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user


@router.get("/users")        
async def get_current_user(db: db_dependency, token: str = Depends(oauth2_bearer)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    user_id: str = payload.get("id")
    if user_id is None:
        return {"error": "no id in token"}
    #user = get_user_by_id(int(user_id))
    user = db.get(User, user_id)
    if user is None:
        return {"error": "no user found with that id"}
    
    return user


def create_access_token(user: User):
    payload = {"sub": user.email, "id": user.id, "role": user.role, "exp": time.time() + ACCESS_TOKEN_EXPIRE_MINUTES * 60}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def generate_restart_token(user: User, delta: timedelta = timedelta(days=3)):
    payload = {"sub": user.email, "id": user.id, "exp": time.time() + delta.total_seconds() + (ACCESS_TOKEN_EXPIRE_MINUTES * 60)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_user_by_id(user_id: int, db: db_dependency):
    return db.query(User).get(user_id)

async def isAuthorized(token: str = Depends(oauth2_bearer)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    credentials_forbidden = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to access this resource")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
        #if(Role != None):
        #    role = payload.get("role")
        #    if(role != Role):
        #        raise credentials_forbidden
    except ExpiredSignatureError:
        raise credentials_forbidden
    except JWTError:
        raise credentials_exception
    
async def decode_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def generate_random_password(length=8):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for _ in range(length))
    return password
