import asyncio
import time
from typing import Annotated
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
)
import json

from jose import JWTError
from sqlmodel import Session


from auth import decode_token
from models import SensorData
from collections import defaultdict
from pydantic import ValidationError
from database import get_session


router = APIRouter(prefix="/sensor", tags=["sensor"])

arduino_clients = set()
dashboard_clients = set()
data_buffer = defaultdict(list)
last_sent_time = time.time()
db_dependency = Annotated[Session, Depends(get_session)]


def items_to_send(sensor_data_list, n=1):
    if len(sensor_data_list) <= n:
        # If there are fewer than n items, send all items
        items_to_send = sensor_data_list
    else:
        # Calculate the step size
        step = len(sensor_data_list) // n
        # Select n evenly spaced items
        items_to_send = [
            sensor_data_list[i] for i in range(0, len(sensor_data_list), step)
        ]
        # Ensure the last item is included
        if items_to_send[-1] != sensor_data_list[-1]:
            items_to_send[-1] = sensor_data_list[-1]
    return items_to_send


@router.websocket("/arduino_ws_no_token")
async def arduino_websocket_no_token(websocket: WebSocket, db: db_dependency):
    try:
        print("Connecting to websocket...")
        await websocket.accept()
    except Exception as e:
        print(f"Failed to connect: {str(e)}")
        return
    # await websocket.accept()
    arduino_clients.add(websocket)
    print(f"Arduino connected: {websocket.client.host}")
    global last_sent_time
    try:
        while True:
            data = await websocket.receive_text()
            try:
                sensor_data = SensorData.model_validate_json(data)
                print(f"Received JSON data from Arduino: {data}")
                # Add SensorData to the list for its device and sensor type
                data_buffer[(sensor_data.device, sensor_data.sensor_type)].append(
                    sensor_data
                )
                db.add(sensor_data)
                if time.time() - last_sent_time >= 1:
                    for dashboard_client in dashboard_clients:
                        for sensor_data_list in data_buffer.values():
                            items = items_to_send(sensor_data_list, n=5)
                            for item in items:
                                await dashboard_client.send_json(item.to_dict())

                    last_sent_time = time.time()
                    data_buffer.clear()
            except ValidationError:
                print(f"Validation error for SensorData: {data}")
                continue
    except asyncio.CancelledError:
        pass
    except WebSocketDisconnect:
        pass
    finally:
        db.commit()
        arduino_clients.remove(websocket)
        print(f"Arduino disconnected: {websocket.client.host}")


@router.websocket("/arduino_ws")
async def arduino_websocket(websocket: WebSocket, token: str):
    try:
        payload = await decode_token(token)
        print("payload:", payload)
        print("token:", token)
    except JWTError:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token"
        )

    await websocket.accept()
    arduino_clients.add(websocket)
    print(f"Arduino connected: {websocket.client.host}")

    try:
        while True:
            data = await websocket.receive_text()
            try:
                json_data = json.loads(data)
                # Process Arduino JSON data as needed
                print(f"Received JSON data from Arduino: {json_data}")
                # Broadcast JSON data to all dashboard clients
                for dashboard_client in dashboard_clients:
                    await dashboard_client.send_json(json_data)
            except json.JSONDecodeError:
                print(f"Invalid JSON data received from Arduino: {data}")
    except asyncio.CancelledError:
        pass
    except WebSocketDisconnect:
        pass
    finally:
        arduino_clients.remove(websocket)
        print(f"Arduino disconnected: {websocket.client.host}")


@router.websocket("/dashboard_ws")
async def dashboard_websocket(websocket: WebSocket):
    await websocket.accept()
    dashboard_clients.add(websocket)
    print(f"Dashboard connected: {websocket.client.host}")

    try:
        while True:
            # Dashboard clients can listen for JSON data sent by Arduino devices
            data = await websocket.receive_json()
            print(f"Received JSON data in dashboard: {data}")
    except asyncio.CancelledError:
        pass
    except WebSocketDisconnect:
        pass
    finally:
        dashboard_clients.remove(websocket)
        print(f"Dashboard disconnected: {websocket.client.host}")
