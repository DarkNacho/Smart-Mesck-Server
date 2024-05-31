from enum import Enum
from pydantic import BaseModel
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


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
    sensor_type: SensorType
    value: float
    time: datetime
    timestamp: Optional[datetime]
    time_in_server: Optional[datetime]

    def __repr__(self):
        return f"SensorData(Id={self.id}, Device={self.device}, SensorType={self.sensor_type}, Value={self.value}, Time={self.time}, TimeStamp={self.timestamp}, TimeInServer={self.time_in_server})"

    # Estos son los datos que estoy utilizando en el arduino_client.py para prueba
    def to_dict(self):
        return {
            "device": self.device,
            "sensor_type": self.sensor_type,
            "value": self.value,
            "time": self.time,
        }
