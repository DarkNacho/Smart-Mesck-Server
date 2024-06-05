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
from models import FileUploadModel

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))


router = APIRouter(prefix="/file", tags=["file"])
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/auth/token")

db_dependency = Annotated[Session, Depends(get_session)]

isAuthorized_dependency = Annotated[dict, Depends(isAuthorized)]


@router.get("/protected-route")
async def protected_route(payload: isAuthorized_dependency):
    email = payload.get("sub")
    user_id = payload.get("id")
    print(payload)
    return {"message": f"You have accessed a protected route with email {email}"}


@router.post("/upload")
async def create_upload_files(db: db_dependency, file: UploadFile = File):

    content = await file.read()
    new_file = FileUploadModel(name=file.filename, content=content)
    db.add(new_file)
    db.commit()
    return {"id": new_file.id, "filename": new_file.name, "hash": new_file.hash}


@router.get("/{file_id}")
async def download_file(file_id: int, db: db_dependency):
    db_file = db.get(FileUploadModel, file_id)
    if db_file is None:
        raise HTTPException(status_code=404, detail="File not found")

    return StreamingResponse(
        io.BytesIO(db_file.content),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{db_file.name}"',
        },
    )
