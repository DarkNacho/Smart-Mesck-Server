from datetime import datetime
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlmodel import Session, select
from database import get_session
from models import GameData, GameDataResponse

router = APIRouter(prefix="/GameData", tags=["GameData"])

db_dependency = Annotated[Session, Depends(get_session)]


@router.get(
    "/all", response_model=List[GameDataResponse], description="Get all game data"
)
async def get_all_game_data(db: db_dependency):
    """
    Obtiene todos los registros de GameData.
    """
    query = select(GameData)
    results = db.execute(query).scalars().all()
    return [GameDataResponse.from_game_data(result) for result in results]


@router.get(
    "/filter", response_model=List[GameDataResponse], description="Filter game data"
)
async def filter_game_data(
    db: db_dependency,
    userID: Optional[str] = Query(None, description="Filter by userID"),
    encounter_id: Optional[str] = Query(None, description="Filter by encounter_id"),
    start_timestamp: Optional[int] = Query(
        None, description="Start of timestamp range (inclusive)"
    ),
    end_timestamp: Optional[int] = Query(
        None, description="End of timestamp range (inclusive)"
    ),
):
    """
    Filtra registros de GameData por userID, encounter_id y/o rango de timestamp.
    Al menos uno de los parámetros debe ser proporcionado.
    """
    if not (userID or encounter_id or start_timestamp or end_timestamp):
        raise HTTPException(
            status_code=400,
            detail="At least one filter parameter (userID, encounter_id, or timestamp range) must be provided",
        )

    query = select(GameData)

    # Agregar filtros opcionales
    if userID:
        query = query.where(GameData.userID == userID)
    if encounter_id:
        query = query.where(GameData.encounter_id == encounter_id)
    if start_timestamp:
        query = query.where(GameData.timestamp >= start_timestamp)
    if end_timestamp:
        query = query.where(GameData.timestamp <= end_timestamp)

    results = db.execute(query).scalars().all()
    return [GameDataResponse.from_game_data(result) for result in results]


@router.get("/{id}", response_model=GameDataResponse, description="Get game data by ID")
async def get_game_data_by_id(id: int, db: db_dependency):
    """
    Obtiene un registro específico de GameData por su ID.
    """
    game_data = db.get(GameData, id)
    if not game_data:
        raise HTTPException(status_code=404, detail="GameData not found")
    return GameDataResponse.from_game_data(game_data)


@router.post(
    "/", response_model=GameDataResponse, description="Create a new GameData entry"
)
async def create_game_data(game_data: GameData, db: db_dependency):
    """
    Crea un nuevo registro de GameData.
    """
    db.add(game_data)
    db.commit()
    db.refresh(game_data)
    return GameDataResponse.from_game_data(game_data)


@router.post(
    "/bulk",
    response_model=List[GameDataResponse],
    description="Create multiple GameData entries",
)
async def create_game_data_bulk(
    db: db_dependency, game_data_list: List[GameData] = Body(...)
):
    """
    Crea múltiples registros de GameData.
    """
    db.add_all(game_data_list)
    db.commit()
    for game_data in game_data_list:
        db.refresh(game_data)
    return [GameDataResponse.from_game_data(game_data) for game_data in game_data_list]
