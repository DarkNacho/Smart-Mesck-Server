from collections import defaultdict
from datetime import datetime

from fastapi.responses import StreamingResponse
from matplotlib import pyplot as plt

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
import io


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

import httpx

import os
from dotenv import load_dotenv


from jose import JWTError
from sqlmodel import Session


from auth import isAuthorized as Authorized, isAuthorizedToken as AuthorizedToken


from database import get_session

from sqlalchemy import func

from models import SensorData


router = APIRouter(prefix="/report", tags=["report"])

db_dependency = Annotated[Session, Depends(get_session)]
isAuthorized = Annotated[Authorized, Depends(Authorized)]
isAuthorizedToken = Annotated[AuthorizedToken, Depends(AuthorizedToken)]

HAPI_FHIR_URL = os.getenv("HAPI_FHIR_URL")


def generate_report_sensor(data):
    story = []
    ## Datos de los encuentros de sensores
    sensorData = defaultdict(lambda: defaultdict(list))

    # Define the title and style
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    report_title = Paragraph("Reporte de Observaciones", title_style)

    # Add the title to the story
    story.append(report_title)
    story.append(Spacer(1, 12))

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
            sensorData[sensor_type]["min"].append(sensor_data["min"])
            sensorData[sensor_type]["max"].append(sensor_data["max"])
            sensorData[sensor_type]["avg"].append(sensor_data["avg"])
            sensorData[sensor_type]["timestamp_epoch"].append(
                sensor_data["timestamp_epoch"]
            )

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

    # Generar y agregar gráficos al PDF
    for sensor_type, stats in sensorData.items():
        plt.figure()
        plt.plot(stats["timestamp_epoch"], stats["min"], label="Min", marker="o")
        plt.plot(stats["timestamp_epoch"], stats["max"], label="Max", marker="o")
        plt.plot(stats["timestamp_epoch"], stats["avg"], label="Avg", marker="o")
        plt.title(f"{sensor_type} Sensor Data")
        plt.xlabel("Day")
        plt.ylabel("Value")
        plt.legend()
        plt.tight_layout()

        # Guardar el gráfico en un buffer
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png")
        img_buffer.seek(0)
        plt.close()

        # Agregar el gráfico al PDF
        story.append(Image(img_buffer))

    return story


def generate_report_medication(medication_data_array):
    story = []

    # Define the title and style
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    report_title = Paragraph("Reporte de Medicaciones", title_style)

    # Add the title to the story
    story.append(report_title)
    story.append(Spacer(1, 12))

    for medication_data in medication_data_array:
        # Agregar subtítulo con el display del code del recurso
        code_display = (
            medication_data.get("medicationCodeableConcept", {})
            .get("coding", [{}])[0]
            .get("display", "")
        )
        code_system = (
            medication_data.get("medicationCodeableConcept", {})
            .get("coding", [{}])[0]
            .get("system", "")
        )
        subtitle = Paragraph(
            f"<b>{code_display}</b> - Sistema: {code_system}", styles["Heading2"]
        )
        story.append(subtitle)
        story.append(Spacer(1, 12))

        # Dosage details
        dosage_text = medication_data.get("dosage", [{}])[0].get("text", "N/A")
        dosage_route = (
            medication_data.get("dosage", [{}])[0]
            .get("route", {})
            .get("coding", [{}])[0]
            .get("display", "N/A")
        )
        dosage_frequency = f"{medication_data.get('dosage', [{}])[0].get('timing', {}).get('repeat', {}).get('frequency', 'N/A')} vez/veces cada {medication_data.get('dosage', [{}])[0].get('timing', {}).get('repeat', {}).get('period', 'N/A')} {medication_data.get('dosage', [{}])[0].get('timing', {}).get('repeat', {}).get('periodUnit', 'N/A')}"
        dosage_amount = f"{medication_data.get('dosage', [{}])[0].get('doseQuantity', {}).get('value', 'N/A')} {medication_data.get('dosage', [{}])[0].get('doseQuantity', {}).get('unit', 'N/A')}"

        # Medication details
        medication_info = [
            [
                "ID de Medicación",
                Paragraph(medication_data.get("id", ""), styles["Normal"]),
            ],
            [
                "Última Actualización",
                Paragraph(
                    medication_data.get("meta", {}).get("lastUpdated", ""),
                    styles["Normal"],
                ),
            ],
            ["Estado", Paragraph(medication_data.get("status", ""), styles["Normal"])],
            ["Medicamento", Paragraph(code_display, styles["Normal"])],
            [
                "Contexto",
                Paragraph(
                    medication_data.get("context", {}).get("display", ""),
                    styles["Normal"],
                ),
            ],
            [
                "Período Efectivo",
                Paragraph(
                    f"Desde: {medication_data.get('effectivePeriod', {}).get('start', '')} Hasta: {medication_data.get('effectivePeriod', {}).get('end', '')}",
                    styles["Normal"],
                ),
            ],
            [
                "Fuente de Información",
                Paragraph(
                    medication_data.get("informationSource", {}).get("display", ""),
                    styles["Normal"],
                ),
            ],
            [
                "Dosificación",
                Paragraph(
                    f"{dosage_text}\nRuta: {dosage_route}\nFrecuencia: {dosage_frequency}\nCantidad: {dosage_amount}",
                    styles["Normal"],
                ),
            ],
        ]

        # Create a table with the medication info
        medication_table = Table(medication_info, colWidths=[2 * inch, 4 * inch])
        medication_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )

        # Add the table to the story
        story.append(medication_table)
        story.append(Spacer(1, 12))

    return story


def generate_report_observation(observation_data_array):
    story = []

    # Define the title and style
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    report_title = Paragraph("Reporte de Observaciones", title_style)

    # Add the title to the story
    story.append(report_title)
    story.append(Spacer(1, 12))

    for observation_data in observation_data_array:
        # Convertir la cadena de fecha a un objeto datetime
        fecha_objeto = datetime.fromisoformat(observation_data["meta"]["lastUpdated"])
        fecha_formateada = fecha_objeto.strftime("%Y-%m-%d %H:%M:%S")

        # Agregar subtítulo con el display del code del recurso
        code_display = observation_data["code"]["coding"][0]["display"]
        code_system = observation_data["code"]["coding"][0]["system"]
        subtitle = Paragraph(
            f"<b>{code_display}</b> - Sistema: {code_system}", styles["Heading2"]
        )
        story.append(subtitle)
        story.append(Spacer(1, 12))

        observation_info = [
            ["ID de Observación", Paragraph(observation_data["id"], styles["Normal"])],
            ["Última Actualización", Paragraph(fecha_formateada, styles["Normal"])],
            ["Estado", Paragraph(observation_data["status"], styles["Normal"])],
            [
                "Categoría",
                Paragraph(
                    observation_data["category"][0]["coding"][0]["display"],
                    styles["Normal"],
                ),
            ],
            [
                "Código",
                Paragraph(
                    observation_data["code"]["coding"][0]["code"], styles["Normal"]
                ),
            ],
            # [
            #    "Paciente",
            #    Paragraph(
            #        f"{observation_data['subject']['display']}", styles["Normal"]
            #    ),
            # ],
            [
                "Encuentro",
                Paragraph(
                    f"{observation_data['encounter']['display']}", styles["Normal"]
                ),
            ],
            ["Emitido el", Paragraph(observation_data["issued"], styles["Normal"])],
            [
                "Performer",
                Paragraph(
                    f"{observation_data['performer'][0]['display']}", styles["Normal"]
                ),
            ],
            ["Valor", Paragraph(observation_data["valueString"], styles["Normal"])],
            [
                "Interpretación",
                Paragraph(
                    ", ".join(
                        [
                            f"{code['display']} (Código: {code['code']})"
                            for code in observation_data["interpretation"][0]["coding"]
                        ]
                    ),
                    styles["Normal"],
                ),
            ],
            ["Notas", Paragraph(observation_data["note"][0]["text"], styles["Normal"])],
        ]

        # Create a table with the observation info
        observation_table = Table(observation_info, colWidths=[2 * inch, 4 * inch])
        observation_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )

        # Add the table to the story
        story.append(observation_table)
        story.append(Spacer(1, 12))

    return story


def generate_report_condition(condition_data_array):
    story = []

    # Define the title and style
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    report_title = Paragraph("Reporte de Condiciones", title_style)

    # Add the title to the story
    story.append(report_title)
    story.append(Spacer(1, 12))

    for condition_data in condition_data_array:
        # Agregar subtítulo con el display del code del recurso
        code_display = condition_data["code"]["coding"][0]["display"]
        code_system = condition_data["code"]["coding"][0]["system"]
        subtitle = Paragraph(
            f"<b>{code_display}</b> - Sistema: {code_system}", styles["Heading2"]
        )
        story.append(subtitle)
        story.append(Spacer(1, 12))

        # Condition details
        condition_info = [
            ["ID de Condición", Paragraph(condition_data["id"], styles["Normal"])],
            [
                "Última Actualización",
                Paragraph(condition_data["meta"]["lastUpdated"], styles["Normal"]),
            ],
            [
                "Estado Clínico",
                Paragraph(
                    condition_data["clinicalStatus"]["coding"][0]["code"],
                    styles["Normal"],
                ),
            ],
            [
                "Código",
                Paragraph(
                    condition_data["code"]["coding"][0]["display"], styles["Normal"]
                ),
            ],
            # [
            #    "Paciente",
            #    Paragraph(condition_data["subject"]["display"], styles["Normal"]),
            # ],
            [
                "Encuentro",
                Paragraph(condition_data["encounter"]["display"], styles["Normal"]),
            ],
            [
                "Registrador",
                Paragraph(condition_data["recorder"]["display"], styles["Normal"]),
            ],
            ["Notas", Paragraph(condition_data["note"][0]["text"], styles["Normal"])],
        ]

        # Create a table with the condition info
        condition_table = Table(condition_info, colWidths=[2 * inch, 4 * inch])
        condition_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )

        # Add the table to the story
        story.append(condition_table)
        story.append(Spacer(1, 12))

    return story


def calculate_age(birthdate):
    today = datetime.today()
    birthdate = datetime.strptime(birthdate, "%Y-%m-%d")
    age = (
        today.year
        - birthdate.year
        - ((today.month, today.day) < (birthdate.month, birthdate.day))
    )
    return age


def get_person_name_as_string(resource):
    name = ""

    # Try to get the name using resource['name'][0]['text']
    if "name" in resource and resource["name"][0].get("text"):
        name = resource["name"][0]["text"]
    elif "name" in resource and resource["name"][0]:
        # Try to get the name using resource['name'][0]['given'] and resource['name'][0]['family']
        given_names = " ".join(resource["name"][0].get("given", []))
        family_name = resource["name"][0].get("family", "")
        name = f"{given_names} {family_name}"
    elif (
        "name" in resource
        and resource["name"][0]
        and resource["name"][0].get("use") == "official"
    ):
        # Try to get the name using resource['name'][0]['prefix'], resource['name'][0]['given'], and resource['name'][0]['family']
        prefix = " ".join(resource["name"][0].get("prefix", []))
        given_names = " ".join(resource["name"][0].get("given", []))
        family_name = resource["name"][0].get("family", "")
        name = f"{prefix} {given_names} {family_name}"

    return name


def generate_report_user(patient):
    story = []

    patient_data = parse_patient_info(patient)
    # Define the title and style
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    report_title = Paragraph("Reporte de Paciente", title_style)

    # Add the title to the story
    story.append(report_title)
    story.append(Spacer(1, 12))

    # Datos personales del paciente

    # patient_age = calculate_age(patient.get("birthDate"))

    patient_info = [
        ["Nombre", patient_data.get("Name")],
        ["RUT", patient_data.get("RUT")],
        ["Email", patient_data.get("Email")],
        ["Celular", patient_data.get("Phone")],
        ["Fecha de Nacimiento", patient_data.get("BirthDate")],
        # [
        #    "Edad",
        #    patient_age,
        # ],  # Aquí ya no es necesario convertir a string, asumiendo que age ya es un string en el modelo
        # ["Estado Civil", patient_data.civil_state],
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

    return story


def generate_pdf_report(
    patient_data,
    condition_data_array=None,
    observation_data_array=None,
    medication_data_array=None,
    sensor_data=None,
):
    # Create a PDF with the patient data, conditions, observations, medications, and sensors
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []

    # Add the patient data to the story (mandatory)
    patient_story = generate_report_user(patient_data)
    story.extend(patient_story)

    # Add the conditions to the story if provided
    if condition_data_array is not None and len(condition_data_array) > 0:
        print("generating condition report")
        condition_story = generate_report_condition(condition_data_array)
        story.extend(condition_story)

    # Add the observations to the story if provided
    if observation_data_array is not None and len(observation_data_array) > 0:
        print("generating observation report")
        observation_story = generate_report_observation(observation_data_array)
        story.extend(observation_story)

    # Add the medications to the story if provided
    if medication_data_array is not None and len(medication_data_array) > 0:
        print("generating medication report")
        medication_story = generate_report_medication(medication_data_array)
        story.extend(medication_story)

    # Add the sensors to the story if provided
    if sensor_data is not None and len(sensor_data) > 0:
        print("generating sensor report")
        sensor_story = generate_report_sensor(sensor_data)
        story.extend(sensor_story)

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


from fastapi import HTTPException
import httpx


async def fetch_resource(resource_type: str, resource_id: str, token: str) -> dict:
    """
    Fetch a resource from the HAPI FHIR server.

    Args:
        resource_type (str): The type of the resource (e.g., "Patient").
        resource_id (str): The ID of the resource.
        token (str): Authorization token.

    Returns:
        dict: The fetched resource.

    Raises:
        HTTPException: If the resource cannot be fetched.
    """
    if not HAPI_FHIR_URL:
        raise HTTPException(status_code=500, detail="HAPI_FHIR_URL is not configured")

    url = f"{HAPI_FHIR_URL}/{resource_type}/{resource_id}"
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=50.0) as client:
        response = await client.get(url, headers=headers)

    if response.status_code != 200:
        response_data = response.json()
        diagnostic_message = response_data.get("issue", [{}])[0].get(
            "diagnostics", "Unknown error"
        )
        raise HTTPException(status_code=response.status_code, detail=diagnostic_message)

    return response.json()


async def fetch_resources(
    resource_type: str,
    params: dict,
    token: str,
) -> dict:
    """
    Fetch a resource from the HAPI FHIR server.

    Args:
        resource_type (str): The type of the resource (e.g., "Patient").
        resource_id (str): The ID of the resource.
        token (str): Authorization token.

    Returns:
        dict: The fetched resource.

    Raises:
        HTTPException: If the resource cannot be fetched.
    """
    if not HAPI_FHIR_URL:
        raise HTTPException(status_code=500, detail="HAPI_FHIR_URL is not configured")

    url = f"{HAPI_FHIR_URL}/{resource_type}"
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=50.0, params=params) as client:
        response = await client.get(url, headers=headers)

    if response.status_code != 200:
        response_data = response.json()
        diagnostic_message = response_data.get("issue", [{}])[0].get(
            "diagnostics", "Unknown error"
        )
        raise HTTPException(status_code=response.status_code, detail=diagnostic_message)

    return response.json()


# Define a function to parse the patient information from the given dictionary
def parse_patient_info(patient):
    # Initialize an empty dictionary to hold the parsed information
    parsed_info = {}

    # Extract and add basic information
    parsed_info["ID"] = patient.get("id", "N/A")

    identifier = patient.get("identifier", [])
    for iden in identifier:
        if iden["system"] == "RUT":
            parsed_info["RUT"] = iden.get("value", "N/A")
    parsed_info["Name"] = " ".join(
        patient.get("name", [{}])[0].get("given", [])
        + [patient.get("name", [{}])[0].get("family", "")]
    )
    parsed_info["Gender"] = patient.get("gender", "N/A")
    parsed_info["BirthDate"] = patient.get("birthDate", "N/A")

    # Extract and add contact information
    telecoms = patient.get("telecom", [])
    for telecom in telecoms:
        if telecom["system"] == "phone":
            parsed_info["Phone"] = telecom.get("value", "N/A")
        elif telecom["system"] == "email":
            parsed_info["Email"] = telecom.get("value", "N/A")

    # Extract and add marital status
    marital_status = (
        patient.get("maritalStatus", {}).get("coding", [{}])[0].get("display", "N/A")
    )
    parsed_info["Marital Status"] = marital_status

    # Extract and add general practitioner information
    practitioners = patient.get("generalPractitioner", [])
    parsed_info["General Practitioners"] = [
        practitioner.get("reference", "N/A") for practitioner in practitioners
    ]

    return parsed_info


@router.get("/{patient_id}")
async def generate_patient_report(
    patient_id: str,
    token: isAuthorizedToken,
    db: db_dependency,
    obs: bool = False,
    med: bool = False,
    cond: bool = False,
    sensor: bool = False,
):
    try:
        patient = await fetch_resource("Patient", patient_id, token)

        observations_data = []
        medication_data = []
        sensor_data = []
        condition_data = []

        if obs:
            data = await fetch_resources("Observation", {"patient": patient_id}, token)
            observations_data = [item["resource"] for item in data.get("entry", [])]

        if sensor:
            sensor_data = await get_sensor_data(patient_id, db)

        if med:
            data = await fetch_resources(
                "MedicationStatement", {"patient": patient_id}, token
            )
            medication_data = [item["resource"] for item in data.get("entry", [])]

        if cond:
            data = await fetch_resources("Condition", {"patient": patient_id}, token)
            condition_data = [item["resource"] for item in data.get("entry", [])]

        # patient_data = await fetch_resource("Patient", patient_id, token)
        # return parse_patient_info(patient)
        # print(patient)
        pdf_file = generate_pdf_report(
            patient_data=patient,
            observation_data_array=observations_data,
            sensor_data=sensor_data,
            medication_data_array=medication_data,
            condition_data_array=condition_data,
        )
        # report = generate_report_user(patient)

        return StreamingResponse(
            io.BytesIO(pdf_file),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=report.pdf"},
        )
    except Exception as e:
        print(e)  # For debugging purposes, consider logging this in production
        raise HTTPException(status_code=500, detail="Internal server error")


async def get_sensor_data(patient_id: str, db: db_dependency):

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
        timestamp_epoch,
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
            "timestamp_epoch": timestamp_epoch,
        }
    return results
