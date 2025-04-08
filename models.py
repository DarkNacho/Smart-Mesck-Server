from enum import Enum
from pydantic import BaseModel
from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger, Text
from typing import Optional, List
from datetime import datetime
from hashlib import sha256
import json


class Token(BaseModel):
    access_token: str
    token_type: str


class User(SQLModel, table=True):
    __tablename__ = "sm_users"
    # id: str = Field(default=None, primary_key=True)
    id: Optional[int] = Field(default=None, primary_key=True)
    fhir_id: Optional[str] = Field(unique=True, default=None, index=True)  # FHIR ID
    rut: str = Field(unique=True, index=True)
    name: str
    hash_password: str
    role: str = Field(index=True)
    secondaryRoles: Optional[str] = Field(index=True)
    email: str = Field(index=True)
    phone_number: str = Field(index=True)
    validate: bool = False

    def to_dict(self):
        return self.to_dict(exclude={"hash_password"})


class SensorType(str, Enum):
    Temperatura = "Temperatura"
    CO2 = "CO2"
    Inercial = "Inercial"
    Dummy = "Dummy"


class SensorData(SQLModel, table=True):
    __tablename__ = "sm_sensor_data"
    id: int = Field(default=None, primary_key=True)
    device: str
    sensor_type: str
    value: float
    timestamp_epoch: int = Field(sa_column=BigInteger)
    timestamp_millis: int
    patient_id: str = Field(index=True)
    encounter_id: str = Field(index=True)

    @property
    def datetime(self):
        return datetime.fromtimestamp(
            self.timestamp_epoch + self.timestamp_millis / 1000.0
        )

    def __repr__(self):
        return f"SensorData(Id={self.id}, Device={self.device}, SensorType={self.sensor_type}, Value={self.value}, TimeEpoch={self.timestamp_epoch}, TimeMiliSec={self.timestamp_millis}, DateTime={self.datetime.isoformat()}, PatientId={self.patient_id}, EncounterId={self.encounter_id})"

    def __str__(self):
        return self.__repr__()

    # Estos son los datos que estoy utilizando en el arduino_client.py para prueba
    def to_dict(self):
        return {
            "device": self.device,
            "sensor_type": self.sensor_type,
            "value": self.value,
            "timestamp_epoch": self.timestamp_epoch,
            "timestamp_millis": self.timestamp_millis,
            "datetime": self.datetime.isoformat(),
            "patient_id": self.patient_id,
            "encounter_id": self.encounter_id,
        }


class FileUploadModel(SQLModel, table=True):
    __tablename__ = "sm_files"
    id: int = Field(default=None, primary_key=True)
    name: str
    content: bytes
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    hash: Optional[str] = Field(default=None)

    def __init__(self, **data):
        super().__init__(**data)
        self.hash = self.generate_hash()

    def generate_hash(self):
        return sha256(self.content).hexdigest()


# First modify your MovimientoRespiracion class to inherit from BaseModel
class MovimientoRespiracion(BaseModel):
    ejeX: List[float] = []
    ejeY: List[float] = []
    timestamps: List[int] = []

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        # Handle the case when created with positional args via legacy constructor
        # This allows backward compatibility
        if "ejeX" in data and isinstance(data["ejeX"], list):
            super().__init__(**data)
        else:
            super().__init__(
                ejeX=data.get("ejeX", []),
                ejeY=data.get("ejeY", []),
                timestamps=data.get("timestamps", []),
            )

    # Keep your existing methods
    def to_dict(self):
        return {
            "ejeX": self.ejeX,
            "ejeY": self.ejeY,
            "timestamps": self.timestamps,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            ejeX=data.get("ejeX", []),
            ejeY=data.get("ejeY", []),
            timestamps=data.get("timestamps", []),
        )

    def __repr__(self):
        return f"MovimientoRespiracion(ejeX={self.ejeX}, ejeY={self.ejeY}, timestamps={self.timestamps})"


class GameData(SQLModel, table=True):
    __tablename__ = "sm_game_data"

    id: int = Field(default=None, primary_key=True)  # Clave primaria autogenerada
    encounter_id: str = Field(index=True)  # Indexado para búsquedas
    userID: str = Field(index=True)  # Indexado para búsquedas
    timestamp: int = Field(sa_column=BigInteger)  # Timestamp en milisegundos

    # Campos opcionales
    playTime: Optional[float] = None
    snowHighestScore: Optional[float] = None
    fruitHighestScore: Optional[float] = None
    relaxHighestScore: Optional[float] = None
    carouselHighestScore: Optional[float] = None

    # Campo para MovimientoRespiracion como JSON (almacenado como texto en SQLite)
    movimientoRespiracion: Optional[str] = Field(
        default=None, sa_column=Field(sa_column=Text)
    )

    # Add a property that's not stored in the database but returns the object
    @property
    def movimiento_resp_obj(self) -> Optional[MovimientoRespiracion]:
        """Returns the MovimientoRespiracion as an object instead of a string"""
        return self.get_movimiento_respiracion()

    def __init__(self, **data):
        if "movimientoRespiracion" in data and isinstance(
            data["movimientoRespiracion"], dict
        ):
            data["movimientoRespiracion"] = json.dumps(data["movimientoRespiracion"])
        super().__init__(**data)
        if "userID" in data:
            self.userID = self.clean_user_id(data["userID"])

    @staticmethod
    def clean_user_id(user_id: str) -> str:
        """
        Limpia el formato del userID eliminando puntos, guiones y convirtiendo a mayúsculas.
        """
        return user_id.replace(".", "").replace("-", "").upper()

    def set_movimiento_respiracion(self, movimiento: MovimientoRespiracion):
        self.movimientoRespiracion = json.dumps(movimiento.to_dict())

    def get_movimiento_respiracion(self) -> Optional[MovimientoRespiracion]:
        if self.movimientoRespiracion:
            return MovimientoRespiracion.from_dict(
                json.loads(self.movimientoRespiracion)
            )
        return None

    def __repr__(self):
        return (
            f"GameData(ID={self.id}, EncounterID={self.encounter_id}, UserID={self.userID}, "
            f"Timestamp={self.timestamp}, PlayTime={self.playTime}, SnowHighestScore={self.snowHighestScore}, "
            f"FruitHighestScore={self.fruitHighestScore}, RelaxHighestScore={self.relaxHighestScore}, "
            f"CarouselHighestScore={self.carouselHighestScore}, MovimientoRespiracion={self.get_movimiento_respiracion()})"
        )

    def __str__(self):
        return self.__repr__()

    def to_dict(self):
        movimiento_data = None
        if self.movimientoRespiracion:
            try:
                # Just parse the JSON string directly
                movimiento_data = json.loads(self.movimientoRespiracion)

            except json.JSONDecodeError:
                movimiento_data = None

        return {
            "id": self.id,
            "encounter_id": self.encounter_id,
            "userID": self.userID,
            "timestamp": self.timestamp,
            "playTime": self.playTime,
            "snowHighestScore": self.snowHighestScore,
            "fruitHighestScore": self.fruitHighestScore,
            "relaxHighestScore": self.relaxHighestScore,
            "carouselHighestScore": self.carouselHighestScore,
            "movimientoRespiracion": movimiento_data,
        }


class GameDataResponse(BaseModel):
    id: int
    encounter_id: str
    userID: str
    timestamp: int
    playTime: Optional[float] = None
    snowHighestScore: Optional[float] = None
    fruitHighestScore: Optional[float] = None
    relaxHighestScore: Optional[float] = None
    carouselHighestScore: Optional[float] = None
    movimientoRespiracion: Optional[MovimientoRespiracion] = None

    @classmethod
    def from_game_data(cls, game_data: GameData) -> "GameDataResponse":
        """Convert a GameData object to a GameDataResponse object"""
        movimiento_obj = None
        if game_data.movimientoRespiracion:
            try:
                data = json.loads(game_data.movimientoRespiracion)
                movimiento_obj = MovimientoRespiracion(**data)
            except (json.JSONDecodeError, ValueError):
                pass

        return cls(
            id=game_data.id,
            encounter_id=game_data.encounter_id,
            userID=game_data.userID,
            timestamp=game_data.timestamp,
            playTime=game_data.playTime,
            snowHighestScore=game_data.snowHighestScore,
            fruitHighestScore=game_data.fruitHighestScore,
            relaxHighestScore=game_data.relaxHighestScore,
            carouselHighestScore=game_data.carouselHighestScore,
            movimientoRespiracion=movimiento_obj,
        )
