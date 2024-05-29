import asyncio
import time
from fastapi import (
    APIRouter,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
)
import json

from jose import JWTError


from auth import decode_token
from models import SensorData
from collections import defaultdict
from pydantic import ValidationError

router = APIRouter(prefix="/sensor", tags=["sensor"])

arduino_clients = set()
dashboard_clients = set()
data_buffer = defaultdict(list)
last_sent_time = time.time()


@router.websocket("/arduino_ws_no_token")
async def arduino_websocket_no_token(websocket: WebSocket):
    await websocket.accept()
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
                if time.time() - last_sent_time >= 1:
                    for dashboard_client in dashboard_clients:
                        for sensor_data_list in data_buffer.values():
                            # Send the last SensorData in the list
                            await dashboard_client.send_json(
                                sensor_data_list[-1].to_dict()
                            )
                    last_sent_time = time.time()
                    data_buffer.clear()  # TODO: Enviarlo a una base de datos antes de limpiar
            except ValidationError:
                print(f"Validation error for SensorData: {data}")
                continue
    except asyncio.CancelledError:
        pass
    except WebSocketDisconnect:
        pass
    finally:
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
