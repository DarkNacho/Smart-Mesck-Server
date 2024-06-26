from enum import Enum
from pydantic import BaseModel
from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger
from typing import Optional
from datetime import datetime
from hashlib import sha256


class Token(BaseModel):
    access_token: str
    token_type: str


class User(SQLModel, table=True):
    __tablename__ = "sm_users"
    id: str = Field(default=None, primary_key=True)
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
