from enum import Enum
from pydantic import validator
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import re

class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    email: str
    rut: str
    hash_password: str
    phone_number: str
    validate : bool = False

class SensorType(str, Enum):
    Temperatura = "Temperatura"
    CO2 = "CO2"
    Inercial = "Inercial"
    
class SensorData(SQLModel, table=True):    
    id: int = Field(default=None, primary_key=True)
    device: str
    sensor_type: SensorType
    value: float
    time: datetime
    timestamp: Optional[datetime] 
    time_in_server: Optional[datetime] 
    
    @validator('time', 'timestamp', 'time_in_server', pre=True)
    def parse_datetime(cls, value):
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value

    def __repr__(self):
        return f"SensorData(Id={self.id}, Device={self.device}, SensorType={self.sensor_type}, Value={self.value}, Time={self.time}, TimeStamp={self.timestamp}, TimeInServer={self.time_in_server})"