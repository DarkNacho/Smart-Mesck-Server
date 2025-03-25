from datetime import timedelta
import io
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Annotated, List
from sqlmodel import Session
from database import get_session

import os
from dotenv import load_dotenv
from auth import isAuthorized
from models import GameData

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))


router = APIRouter(prefix="/GameData", tags=["GameData"])
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/GameData")

db_dependency = Annotated[Session, Depends(get_session)]

isAuthorized_dependency = Annotated[dict, Depends(isAuthorized)]


@router.post(
    "/", response_model=GameData, status_code=201, description="Add a new game data"
)
async def add_game_data(db: db_dependency, data: GameData):
    db.add(data)
    db.commit()
    return data.to_dict()


@router.get("/{userID}", response_model=GameData, description="Get game data by userID")
async def get_game_Data(userID: str, db: db_dependency):
    db_file = db.get(GameData, userID)
    if db_file is None:
        raise HTTPException(status_code=404, detail="Not found")

    return db_file.to_dict()


@router.get("/all", response_model=List[GameData], description="Get all game data")
async def all(db: db_dependency):
    db_file = db.get(GameData)
    if db_file is None:
        raise HTTPException(status_code=404, detail="Not found")

    return db_file.to_dict()
