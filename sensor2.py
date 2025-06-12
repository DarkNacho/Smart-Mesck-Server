import asyncio
from datetime import datetime, timezone
import time
from typing import Annotated, Dict, List
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
from fastapi.responses import StreamingResponse
import requests
import os
from dotenv import load_dotenv


from jose import JWTError
from sqlmodel import Session


from auth import decode_token
from models import SensorData
from collections import defaultdict
from pydantic import BaseModel, ValidationError

from sqlalchemy import func
from auth import isAuthorized
from database import get_session
from jwt import generate_token_with_payload as generate_token
from auth import validate_resource_fhir
from utils import create_resource, get_fhir_id

load_dotenv()

router = APIRouter(prefix="/sensor2", tags=["sensor"])

arduino_clients = set()
dashboard_clients = defaultdict(list)
data_buffer = defaultdict(list)
patients_to_monitor = set()

# last_sent_time = time.time()

HAPI_FHIR_URL = os.getenv("HAPI_FHIR_URL")
SMART_MESCK_URL = os.getenv("SMART_MESCK_URL")


isAuthorized_dependency = Annotated[dict, Depends(isAuthorized)]
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


@router.websocket("/arduino_ws")
async def arduino_websocket(
    websocket: WebSocket,
    token: str,
    db: db_dependency,
    encounter_id: str = None,
    rut: str = None,
):
    try:
        print("Connecting to websocket...")
        payload = await decode_token(token)
        patient_id = payload.get("id")
        print("payload:", payload)
        print("token:", token)
        await websocket.accept()
        if rut:
            print("fetching id for Rut:", rut)
            try:
                response_patient = get_fhir_id(rut, db)
                print("response_patient:", response_patient)
                fhir_id = response_patient.get("fhir_id")
                if fhir_id:
                    print(f"FHIR ID for patient_rut {rut}: {fhir_id}")
                    await websocket.send_text(f"fhir_id: {fhir_id}")
                    # Use the found fhir_id as the patient_id
                    patient_id = fhir_id
                else:
                    print(f"No user found with RUT: {rut}")
                    await websocket.send_text(f"error: No user found with RUT {rut}")
            except Exception as e:
                print(f"Error fetching FHIR ID for RUT {rut}: {str(e)}")
                await websocket.send_text(f"error: {str(e)}")

        if not encounter_id:
            print("No encounter ID, creating new encounter...")

            encounter_template = {
                "resourceType": "Encounter",
                "status": "in-progress",
                "subject": {
                    "reference": f"Patient/{patient_id}",
                    "display": payload.get("name"),
                },
                "period": {
                    "start": datetime.now(timezone.utc).isoformat(),
                    "end": None,
                },
                "type": [
                    {
                        "coding": [
                            {
                                "system": "CTTN",
                                "code": "SENSOR-MONITOR",
                                "display": "Sensor Monitoring Encounter",
                            }
                        ]
                    }
                ],
            }

            try:
                print("Attempting to create encounter resource...")
                response_encounter = await create_resource(
                    "Encounter", encounter_template, token
                )
                encounter_id = response_encounter.get("id")
                print("Encounter created:", response_encounter)
                print("Encounter ID:", encounter_id)
                await websocket.send_text(f"encounter_id: {encounter_id}")
            except Exception as e:
                print(f"Failed to create encounter: {str(e)}")
                # Use a temporary ID so the connection can continue
                encounter_id = f"temp_{patient_id}_{int(time.time())}"
                await websocket.send_text(f"encounter_id: {encounter_id}")
                await websocket.send_text(f"encounter_creation_error: {str(e)}")

    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token"
        )
    except Exception as e:
        print(f"Failed to connect: {str(e)}")
        return

    # await websocket.accept()
    data_buffer.clear()  # Clear the data buffer for this connection
    arduino_clients.add(websocket)
    patients_to_monitor.add(patient_id)

    print(f"Arduino connected: {websocket.client.host}")
    last_sent_time = time.time()

    async def send_keep_alive():
        while True:
            await asyncio.sleep(2)  # Send a ping every 10 seconds
            try:
                await websocket.send_text("stay alive")
            except WebSocketDisconnect:
                break

    keep_alive_task = asyncio.create_task(send_keep_alive())

    try:
        while True:
            data = await websocket.receive_text()
            if data == "stay alive":
                continue
            if data == "ping":
                await websocket.send_text("pong")
                continue

            try:
                sensor_data = SensorData.model_validate_json(data)
                # sensor_data.encounter_id = encounter_id
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
                await websocket.send_text("Validation error: " + data)
                continue
    except asyncio.CancelledError:
        pass
    except WebSocketDisconnect:
        pass
    finally:
        keep_alive_task.cancel()
        db.commit()
        arduino_clients.remove(websocket)
        patients_to_monitor.remove(patient_id)
        print(f"Arduino disconnected: {websocket.client.host}")


@router.websocket("/dashboard_ws")
async def dashboard_websocket(websocket: WebSocket, token: str, patient_id: str):
    try:
        payload = await decode_token(token)
        print("payload:", payload)
        print("token:", token)
        print("patient_id:", patient_id)

        if validate_resource_fhir(token, "Patient", patient_id):
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

    # Check if the patient is being monitored
    # if patient_id not in patients_to_monitor:
    #    await websocket.send_json({"message": "No patient connected to monitor"})
    # else:
    #    await websocket.send_json(
    #        {"message": "Patient is being monitored but no data is being received"}
    #    )

    try:
        while True:
            # await websocket.send_json(
            #    {"message": f"Connected to dashboard for patient_id {patient_id}"}
            # )
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


@router.websocket("/dashboard_ws_public")
async def dashboard_websocket(websocket: WebSocket, token: str):
    try:
        payload = await decode_token(token)
        print("payload:", payload)
        print("token:", token)
        # print("patient_id:", patient_id)

        patient_id = payload.get("patient_id")

        if patient_id:
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
            websocket.send_json({"message": "Connected"})
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


import qrcode
from io import BytesIO


@router.get("/share_sensor")
async def share_sensor(payload: isAuthorized_dependency):
    patient_id = payload.get("id")
    token = generate_token({"patient_id": patient_id})

    url_generated = f"{SMART_MESCK_URL}/PublicSensor/{token}"

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=15,
        border=1,
    )
    qr.add_data(url_generated)
    qr.make(fit=True)

    # Create an image from the QR Code instance
    img = qr.make_image(fill="black", back_color="white")

    # Save the image to a BytesIO object
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    return StreamingResponse(img_byte_arr, media_type="image/png")


@router.get("/data/{encounter_id}")
async def get_sensor_data(encounter_id: str, db: db_dependency):
    sensor_data = (
        db.query(SensorData).filter(SensorData.encounter_id == encounter_id).all()
    )
    # return sample_by_sensor_type(sensor_data, 5)
    return sensor_data


def uniform_sample(
    sensor_data: List[SensorData], desired_samples: int
) -> List[SensorData]:
    if not sensor_data:
        return []

    # Calculate the total duration in seconds
    start_time = min(data.timestamp_epoch for data in sensor_data)
    end_time = max(data.timestamp_epoch for data in sensor_data)
    duration_seconds = (end_time - start_time) / 1000  # Convert milliseconds to seconds

    # Calculate samples per second
    total_samples = len(sensor_data)
    samples_per_second = total_samples / duration_seconds

    # Calculate step size
    step = int(total_samples / desired_samples)

    # Select samples uniformly
    sampled_data = [sensor_data[i] for i in range(0, total_samples, step)]

    # Ensure the number of samples matches the requested number
    return sampled_data[:desired_samples]


class SensorStats:

    def __init__(self, minValue: float, maxValue: float, avgValue: float):
        self.minValue = minValue
        self.maxValue = maxValue
        self.avgValue = avgValue


class Sensor:
    def __init__(self, data: List[SensorData], stats: SensorStats):
        self.data = data
        self.stats = stats


def sample_by_sensor_type(
    sensor_data: List[SensorData], desired_samples: int
) -> Dict[str, Dict[str, Sensor]]:
    # Group data by device and sensor_type
    grouped_data = defaultdict(lambda: defaultdict(list))
    for data in sensor_data:
        grouped_data[data.device][data.sensor_type].append(data)

    # Apply uniform_sample to each group and store the results
    sampled_data = defaultdict(lambda: defaultdict(Sensor))
    for device, sensors in grouped_data.items():
        for sensor_type, data in sensors.items():
            sampled = uniform_sample(data, desired_samples)
            stats = SensorStats(
                minValue=min(data.value for data in sampled),
                maxValue=max(data.value for data in sampled),
                avgValue=sum(data.value for data in sampled) / len(sampled),
            )
            sampled_data[device][sensor_type] = Sensor(sampled, stats)

    return sampled_data
