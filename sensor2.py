import asyncio
from datetime import datetime
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
from database import get_session

from sqlalchemy import func


load_dotenv()

router = APIRouter(prefix="/sensor2", tags=["sensor"])

arduino_clients = set()
dashboard_clients = defaultdict(list)
data_buffer = defaultdict(list)

last_sent_time = time.time()
db_dependency = Annotated[Session, Depends(get_session)]

HAPI_FHIR_URL = os.getenv("HAPI_FHIR_URL")


class PatientData(BaseModel):
    nombre: str
    rut: str
    email: str
    cel: str
    birthday_date: str
    civil_state: str


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
    global last_sent_time

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

                # db.add(sensor_data)

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
        pass
    except WebSocketDisconnect:
        pass
    finally:
        # db.commit()
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


@router.get("/report/{patient_id}")
async def get_report(patient_id: str, patient_data: PatientData, db: db_dependency):
    # Assuming the database supports these functions directly
    query_result = (
        db.query(
            SensorData.encounter_id,
            SensorData.sensor_type,
            func.min(SensorData.value).label("min_value"),
            func.max(SensorData.value).label("max_value"),
            func.avg(SensorData.value).label("avg_value"),
            func.count(SensorData.value).label("count"),
            func.min(SensorData.timestamp_epoch).label("start_time"),
            func.max(SensorData.timestamp_epoch).label("end_time"),
        )
        .filter(SensorData.patient_id == patient_id)
        .group_by(SensorData.encounter_id, SensorData.sensor_type)
        .all()
    )

    # Preparing the results to return
    results = defaultdict(lambda: defaultdict(dict))
    for (
        encounter_id,
        sensor_type,
        min_value,
        max_value,
        avg_value,
        count,
        start_time,
        end_time,
    ) in query_result:
        start_datetime = datetime.fromtimestamp(start_time)
        end_datetime = datetime.fromtimestamp(end_time)
        duration = end_datetime - start_datetime

        results[encounter_id][sensor_type] = {
            "min": round(min_value, 2),
            "max": round(max_value, 2),
            "avg": round(avg_value, 2),
            "count": count,
            "day": start_datetime.strftime("%d-%m-%Y"),
            "start": start_datetime.strftime("%H:%M:%S"),
            "end": end_datetime.strftime("%H:%M:%S"),
            "duration": str(duration).split(".")[0],  # Format duration to HH:MM:SS
        }
    pdf_file = generate_pdf_report(results, patient_data)
    return StreamingResponse(
        pdf_file,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=report.pdf"},
    )


from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
from reportlab.lib import colors
from reportlab.lib.units import inch
import io


def calculate_age(birthdate):
    today = datetime.today()
    birthdate = datetime.strptime(birthdate, "%Y-%m-%d")
    age = (
        today.year
        - birthdate.year
        - ((today.month, today.day) < (birthdate.month, birthdate.day))
    )
    return age


def generate_pdf_report(data, patient_data: PatientData):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []

    # Define the title and style
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    report_title = Paragraph("Reporte de Paciente", title_style)

    # Add the title to the story
    story.append(report_title)
    story.append(Spacer(1, 12))

    # Calcular la edad del paciente
    patient_age = calculate_age(patient_data.birthday_date)

    # Datos personales del paciente
    patient_info = [
        ["Nombre", patient_data.nombre],
        ["RUT", patient_data.rut],
        ["Email", patient_data.email],
        ["Celular", patient_data.cel],
        ["Fecha de Nacimiento", patient_data.birthday_date],
        [
            "Edad",
            patient_age,
        ],  # Aquí ya no es necesario convertir a string, asumiendo que age ya es un string en el modelo
        ["Estado Civil", patient_data.civil_state],
    ]

    patient_table = Table(patient_info, colWidths=[2 * inch, 4 * inch])
    patient_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
            ]
        )
    )

    story.append(patient_table)
    story.append(Spacer(1, 12))

    ## Datos de los encuentros de sensores

    for encounter_id, encounter_data in data.items():
        encounter_header = [[encounter_id]]
        encounter_table_data = [
            [
                "Sensor Type",
                "Min",
                "Max",
                "Avg",
                "Count",
                "Day",
                "Start",
                "End",
                "Duration",
            ]
        ]

        for sensor_type, sensor_data in encounter_data.items():
            row = [sensor_type]
            row.extend(
                [
                    sensor_data["min"],
                    sensor_data["max"],
                    sensor_data["avg"],
                    sensor_data["count"],
                    sensor_data["day"],
                    sensor_data["start"],
                    sensor_data["end"],
                    sensor_data["duration"],
                ]
            )
            encounter_table_data.append(row)

        header_table = Table(encounter_header)
        header_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTSIZE", (0, 0), (-1, -1), 14),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ]
            )
        )

        encounter_table = Table(encounter_table_data)
        encounter_table.setStyle(
            TableStyle(
                [
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
                    ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ]
            )
        )

        story.append(header_table)
        story.append(encounter_table)

    doc.build(story)
    buffer.seek(0)
    return buffer
