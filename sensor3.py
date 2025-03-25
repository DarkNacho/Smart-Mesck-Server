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
import requests
import os
from dotenv import load_dotenv


from jose import JWTError
from sqlmodel import Session


from auth import decode_token
from models import SensorData
from collections import defaultdict
from pydantic import ValidationError
from database import get_session

load_dotenv()

router = APIRouter(prefix="/sensor2", tags=["sensor"])

arduino_clients = set()
dashboard_clients = defaultdict(list)
data_buffer = defaultdict(list)


db_dependency = Annotated[Session, Depends(get_session)]

HAPI_FHIR_URL = os.getenv("HAPI_FHIR_URL")


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


def validate_patient(token: str, patient_id: str) -> bool:
    if not token or not patient_id:
        raise ValueError("Token and patient_id must not be empty")

    headers = {"Authorization": f"Bearer {token}"}
    print("headers:", headers)
    try:
        response = requests.get(
            f"{HAPI_FHIR_URL}/Patient/{patient_id}", headers=headers
        )  ## call the FHIR server to get the patient data, if you can get it is valid and you actually have authorization to access it.
        response.raise_for_status()
        return True
    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return False
    except Exception as err:
        print(f"Other error occurred: {err}")
        return False


@router.websocket("/arduino_ws")
async def arduino_websocket(websocket: WebSocket, token: str, db: db_dependency):
    try:
        print("Connecting to websocket...")
        payload = await decode_token(token)
        print("payload:", payload)
        print("token:", token)
        await websocket.accept()
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token"
        )
    except Exception as e:
        print(f"Failed to connect: {str(e)}")
        return

    # await websocket.accept()
    arduino_clients.add(websocket)
    print(f"Arduino connected: {websocket.client.host}")
    last_sent_time = time.time()

    try:
        while True:
            data = await websocket.receive_text()

            try:
                sensor_data = SensorData.model_validate_json(data)
                print(f"Received JSON data from Arduino: {sensor_data}")
                # Add SensorData to the list for its device and sensor type
                data_buffer[(sensor_data.device, sensor_data.sensor_type)].append(
                    sensor_data
                )

                db.add(sensor_data)

                if time.time() - last_sent_time >= 1:
                    for dashboard_client in dashboard_clients[
                        sensor_data.patient_id
                    ]:  # send data to all dashboard clients (broadcasting)
                        for sensor_data_list in data_buffer.values():
                            items = items_to_send(sensor_data_list, n=2)
                            for item in items:
                                await dashboard_client.send_json(item.to_dict())

                    last_sent_time = time.time()
                    data_buffer.clear()
            except ValidationError:
                print(f"Validation error for SensorData: {data}")
                continue
    except asyncio.CancelledError:
        print("Cancelled error")
        pass
    except WebSocketDisconnect:
        print("Websocket disconnected")
        pass
    finally:
        db.commit()
        arduino_clients.remove(websocket)
        print(f"Arduino disconnected: {websocket.client.host}")


@router.websocket("/dashboard_ws")
async def dashboard_websocket(websocket: WebSocket, token: str, patient_id: str):
    try:
        payload = await decode_token(token)
        print("payload:", payload)
        print("token:", token)
        print("patient_id:", patient_id)

        if validate_patient(token, patient_id):
            await websocket.accept()
        else:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)

    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token"
        )
    except Exception as e:
        print(f"Failed to connect: {str(e)}")
        return

    dashboard_clients[patient_id].append(
        websocket
    )  ## use the patient_id as key to store the websocket that the practitioner wants to monitor
    # dashboard_clients.add(websocket)
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
        dashboard_clients[patient_id].remove(websocket)
        print(f"Dashboard disconnected: {websocket.client.host}")
