from enum import Enum
from pydantic import BaseModel
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    
class User(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    rut: str = Field(unique=True, index=True)
    hash_password: str
    phone_number: str = Field(unique=True, index=True)
    validate : bool = False
    role: str = Field(index=True)

    def to_dict(self):
        return self.to_dict(exclude={"hash_password"})
            
class SensorType(str, Enum):
    Temperatura = "Temperatura"
    CO2 = "CO2"
    Inercial = "Inercial"
    
class SensorData(SQLModel, table=True):    
    id: str = Field(default=None, primary_key=True)
    device: str
    sensor_type: SensorType
    value: float
    time: datetime
    timestamp: Optional[datetime] 
    time_in_server: Optional[datetime] 
    
    def __repr__(self):
        return f"SensorData(Id={self.id}, Device={self.device}, SensorType={self.sensor_type}, Value={self.value}, Time={self.time}, TimeStamp={self.timestamp}, TimeInServer={self.time_in_server})"