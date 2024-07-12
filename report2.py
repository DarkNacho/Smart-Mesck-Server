from datetime import datetime
import io
import os
from fastapi.responses import StreamingResponse
import pdfkit
from jinja2 import Environment, FileSystemLoader
import tempfile


from typing import Annotated
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

import httpx

from sqlalchemy import func
from sqlmodel import Session


from auth import isAuthorized as Authorized, isAuthorizedToken as AuthorizedToken


from database import get_session
from models import SensorData


router = APIRouter(prefix="/report", tags=["report"])

db_dependency = Annotated[Session, Depends(get_session)]
isAuthorized = Annotated[Authorized, Depends(Authorized)]
isAuthorizedToken = Annotated[AuthorizedToken, Depends(AuthorizedToken)]

HAPI_FHIR_URL = os.getenv("HAPI_FHIR_URL")


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
            pass
            sensor_data = await get_sensor_data(patient_id, db)

        if med:
            data = await fetch_resources(
                "MedicationStatement", {"patient": patient_id}, token
            )
            medication_data = [item["resource"] for item in data.get("entry", [])]

        if cond:
            data = await fetch_resources("Condition", {"patient": patient_id}, token)
            condition_data = [item["resource"] for item in data.get("entry", [])]

        pdf_file = generate_report(
            patient_data=patient,
            observation_data_array=observations_data,
            sensor_data=sensor_data,
            medication_data_array=medication_data,
            condition_data_array=condition_data,
        )

        # patient_data = await fetch_resource("Patient", patient_id, token)
        # return parse_patient_info(patient)
        # print(patient)
        # pdf_file = generate_pdf_report(
        #    patient_data=patient,
        #    observation_data_array=observations_data,
        #    sensor_data=sensor_data,
        #    medication_data_array=medication_data,
        #    condition_data_array=condition_data,
        # )
        # report = generate_report_user(patient)

        return StreamingResponse(
            io.BytesIO(pdf_file),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=report.pdf"},
        )
    except Exception as e:
        print(e)  # For debugging purposes, consider logging this in production
        raise HTTPException(status_code=500, detail="Internal server error")


import matplotlib.pyplot as plt
import io
import base64
from collections import defaultdict


def generate_report(
    patient_data,
    condition_data_array=None,
    observation_data_array=None,
    medication_data_array=None,
    sensor_data=None,
):

    html_data = patient_general_info_report(patient_data)

    # Add the conditions to the story if provided
    if condition_data_array is not None and len(condition_data_array) > 0:
        print("generating condition report")
        html_data += condition_report(condition_data_array)

    # Add the observations to the story if provided
    if observation_data_array is not None and len(observation_data_array) > 0:
        print("generating observation report")
        html_data += observation_report(observation_data_array)

    # Add the medications to the story if provided
    if medication_data_array is not None and len(medication_data_array) > 0:
        print("generating medication report")
        html_data += medication_report(medication_data_array)

    # Add the sensors to the story if provided
    if sensor_data is not None and len(sensor_data) > 0:
        print("generating sensor report")
        html_data += sensor_report(sensor_data)
        # story.extend(sensor_story)

    return generate_pdf_to_byte_array(html_data)


def sensor_report(data):

    context_title = {
        "title": "Reporte Sensores",
        "img_path": os.path.abspath("icon_sensores.png"),
    }

    html = render_template("template_title.html", context_title)
    # html = ""
    sensorData = defaultdict(lambda: defaultdict(list))

    for encounter_id, encounter_data in data.items():

        header_table = [
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

        for sensor_type, sensor_data in encounter_data.items():
            sensorData[sensor_type]["min"].append(sensor_data["min"])
            sensorData[sensor_type]["max"].append(sensor_data["max"])
            sensorData[sensor_type]["avg"].append(sensor_data["avg"])
            sensorData[sensor_type]["timestamp_epoch"].append(
                sensor_data["timestamp_epoch"]
            )

            row = [{"value": sensor_type}]
            row.extend(
                [
                    {"value": sensor_data["min"]},
                    {"value": sensor_data["max"]},
                    {"value": sensor_data["avg"]},
                    {"value": sensor_data["count"]},
                    {"value": sensor_data["day"]},
                    {"value": sensor_data["start"]},
                    {"value": sensor_data["end"]},
                    {"value": sensor_data["duration"]},
                ]
            )

        context = {
            "title": f"Encounter: {encounter_id}",
            "table_data": row,
            "header_list": header_table,
        }
        html += render_template("template_sensor.html", context)

    context_title = {
        "title": "Gráficas Reporte Sensores",
        "img_path": os.path.abspath("icon_sensores.png"),
    }

    html += render_template("template_title.html", context_title)

    for sensor_type, stats in sensorData.items():
        plt.figure()
        plt.plot(stats["timestamp_epoch"], stats["min"], label="Min", marker="o")
        plt.plot(stats["timestamp_epoch"], stats["max"], label="Max", marker="o")
        plt.plot(stats["timestamp_epoch"], stats["avg"], label="Avg", marker="o")
        # plt.title(f"{sensor_type} Sensor Data")
        plt.xlabel("Day")
        plt.ylabel("Value")
        plt.legend()
        plt.tight_layout()

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png")
        plt.close()
        img_buffer.seek(0)
        img_data = base64.b64encode(img_buffer.getvalue()).decode("utf-8")

        context_graph = {
            "title": f"{sensor_type} Sensor Data",
            "img_path": os.path.abspath("icon_graph.png"),
            "img_data": img_data,
        }
        html += render_template("template_graph.html", context_graph)
        # html += f'<img src="data:image/png;base64,{img_data}"/>'

    return html


def medication_report(medication_data_array):
    context_title = {
        "title": "Reporte Medicamentos",
        "img_path": os.path.abspath("icon_med.png"),
    }

    html = render_template("template_title.html", context_title)
    # html = ""

    for medication_data in medication_data_array:
        # Agregar subtítulo con el display del code del recurso
        code_display = (
            medication_data.get("medicationCodeableConcept", {})
            .get("coding", [{}])[0]
            .get("display", "N/A")
        )
        code_system = (
            medication_data.get("medicationCodeableConcept", {})
            .get("coding", [{}])[0]
            .get("system", "N/A")
        )
        code = (
            medication_data.get("medicationCodeableConcept", {})
            .get("coding", [{}])[0]
            .get("code", "N/A")
        )

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

        last_updated = medication_data.get("meta", {}).get("lastUpdated", "N/A")
        if last_updated != "N/A":
            last_updated_obj = datetime.fromisoformat(last_updated)
            last_updated_formatted = last_updated_obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            last_updated_formatted = "N/A"

        # Formatear effectivePeriod start
        effective_start = medication_data.get("effectivePeriod", {}).get("start", "N/A")
        if effective_start != "N/A":
            effective_start_obj = datetime.fromisoformat(effective_start)
            effective_start_formatted = effective_start_obj.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        else:
            effective_start_formatted = "N/A"

        # Formatear effectivePeriod end
        effective_end = medication_data.get("effectivePeriod", {}).get("end", "N/A")
        if effective_end != "N/A":
            effective_end_obj = datetime.fromisoformat(effective_end)
            effective_end_formatted = effective_end_obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            effective_end_formatted = "N/A"

        medication_info = [
            # {
            #    "name": "ID de Medicación",
            #    "value": medication_data.get("id", "N/A"),
            #    "style": "Normal",
            # },
            {
                "name": "Última Actualización",
                "value": last_updated_formatted,
                "style": "Normal",
            },
            # {
            #    "name": "Estado",
            #    "value": medication_data.get("status", "N/A"),
            #    "style": "Normal",
            # },
            # {
            #    "name": "Medicamento",
            #    "value": code_display,
            #    "style": "Normal",
            # },
            # {
            #    "name": "Contexto",
            #    "value": medication_data.get("context", {}).get("display", "N/A"),
            #    "style": "Normal",
            # },
            {
                "name": "Período Efectivo",
                "value": f"Desde: {effective_start_formatted} Hasta: {effective_end_formatted}",
                "style": "Normal",
            },
            # {
            #    "name": "Fuente de Información",
            #    "value": medication_data.get("informationSource", {}).get(
            #        "display", "N/A"
            #    ),
            #    "style": "Normal",
            # },
            {
                "name": "Dosificación",
                "value": f"{dosage_text}, Ruta: {dosage_route}, Frecuencia: {dosage_frequency}, Cantidad: {dosage_amount}",
                "style": "Normal",
            },
        ]

        context = {
            "title": code_display,
            "subtitle": f"System: {code_system} - Code: {code}",
            "table_data": medication_info,
        }

        html += render_template("template_report.html", context)

    return html


def observation_report(observations):
    context_title = {
        "title": "Reporte Observaciones",
        "img_path": os.path.abspath("icon_obs.png"),
    }

    html = render_template("template_title.html", context_title)
    # html = ""
    for observation_data in observations:
        # Convertir la cadena de fecha a un objeto datetime
        fecha_objeto = datetime.fromisoformat(
            observation_data.get("meta", {}).get("lastUpdated", "1900-01-01T00:00:00")
        )
        fecha_formateada = fecha_objeto.strftime("%Y-%m-%d %H:%M:%S")

        issued_value = observation_data.get("issued", "N/A")
        if issued_value != "N/A":
            issued_objeto = datetime.fromisoformat(issued_value)
            issued_formateada = issued_objeto.strftime("%Y-%m-%d %H:%M:%S")
        else:
            issued_formateada = "N/A"

        # Agregar subtítulo con el display del code del recurso
        code_display = (
            observation_data.get("code", {})
            .get("coding", [{}])[0]
            .get("display", "N/A")
        )
        code_system = (
            observation_data.get("code", {}).get("coding", [{}])[0].get("system", "N/A")
        )

        code = (
            observation_data.get("code", {}).get("coding", [{}])[0].get("code", "N/A")
        )

        observation_info = [
            # {
            #    "name": "ID de Observación",
            #    "value": observation_data.get("id", "N/A"),
            #    "style": "Normal",
            # },
            {
                "name": "Última Actualización",
                "value": fecha_formateada,
                "style": "Normal",
            },
            # {
            #    "name": "Estado",
            #    "value": observation_data.get("status", "N/A"),
            #    "style": "Normal",
            # },
            # {
            #    "name": "Categoría",
            #    "value": observation_data.get("category", [{}])[0]
            #    .get("coding", [{}])[0]
            #    .get("display", "N/A"),
            #    "style": "Normal",
            # },
            # {
            #    "name": "Código",
            #    "value": observation_data.get("code", {})
            #    .get("coding", [{}])[0]
            #    .get("code", "N/A"),
            #    "style": "Normal",
            # },
            # {
            #    "name": "Encuentro",
            #    "value": observation_data.get("encounter", {}).get("display", "N/A"),
            #    "style": "Normal",
            # },
            {
                "name": "Emitido el",
                "value": issued_formateada,
                "style": "Normal",
            },
            {
                "name": "Performer",
                "value": observation_data.get("performer", [{}])[0].get(
                    "display", "N/A"
                ),
                "style": "Normal",
            },
            {
                "name": "Valor",
                "value": observation_data.get("valueString", "N/A"),
                "style": "Normal",
            },
            # {
            #    "name": "Interpretación",
            #    "value": ", ".join(
            #        [
            #            f"{code.get('display', 'N/A')} (Código: {code.get('code', 'N/A')})"
            #            for code in observation_data.get("interpretation", [{}])[0].get(
            #                "coding", []
            #            )
            #        ]
            #    ),
            #    "style": "Normal",
            # },
            {
                "name": "Notas",
                "value": observation_data.get("note", [{}])[0].get("text", "N/A"),
                "style": "Normal",
            },
        ]

        context = {
            "title": code_display,
            "subtitle": f"System: {code_system} - Code: {code}",
            "table_data": observation_info,
        }

        html += render_template("template_report.html", context)

    return html


def condition_report(condition_data_array):
    context_title = {
        "title": "Reporte Condiciones",
        "img_path": os.path.abspath("icon_cond.png"),
    }

    html = render_template("template_title.html", context_title)
    # html = ""

    for condition_data in condition_data_array:
        # Convertir la cadena de fecha a un objeto datetime
        fecha_objeto = datetime.fromisoformat(
            condition_data.get("meta", {}).get("lastUpdated", "1900-01-01T00:00:00")
        )
        fecha_formateada = fecha_objeto.strftime("%Y-%m-%d %H:%M:%S")

        # Agregar subtítulo con el display del code del recurso
        code_display = (
            condition_data.get("code", {}).get("coding", [{}])[0].get("display", "N/A")
        )
        code_system = (
            condition_data.get("code", {}).get("coding", [{}])[0].get("system", "N/A")
        )

        code = condition_data.get("code", {}).get("coding", [{}])[0].get("code", "N/A")

        condition_info = [
            # {
            #    "name": "ID de Condición",
            #    "value": condition_data.get("id", "N/A"),
            #    "style": "Normal",
            # },
            {
                "name": "Última Actualización",
                "value": fecha_formateada,
                "style": "Normal",
            },
            # {
            #    "name": "Estado Clínico",
            #    "value": condition_data.get("clinicalStatus", {})
            #    .get("coding", [{}])[0]
            #    .get("code", "N/A"),
            #    "style": "Normal",
            # },
            # {
            #    "name": "Código",
            #    "value": condition_data.get("code", {})
            #    .get("coding", [{}])[0]
            #    .get("display", "N/A"),
            #    "style": "Normal",
            # },
            # {
            #    "name": "Encuentro",
            #    "value": condition_data.get("encounter", {}).get("display", "N/A"),
            #    "style": "Normal",
            # },
            {
                "name": "Registrador",
                "value": condition_data.get("recorder", {}).get("display", "N/A"),
                "style": "Normal",
            },
            {
                "name": "Notas",
                "value": condition_data.get("note", [{}])[0].get("text", "N/A"),
                "style": "Normal",
            },
        ]

        context = {
            "title": code_display,
            "subtitle": f"System: {code_system} - Code: {code}",
            "table_data": condition_info,
        }

        html += render_template("template_report.html", context)

    return html


def calculate_age(birthdate: datetime):
    today = datetime.today()
    age = (
        today.year
        - birthdate.year
        - ((today.month, today.day) < (birthdate.month, birthdate.day))
    )
    return age


def patient_general_info_report(patient):
    context_title = {
        "title": "Reporte Paciente",
        "img_path": os.path.abspath("icon_user.png"),
    }

    html = render_template("template_title.html", context_title)
    # html = ""
    patient_data = parse_patient_info(patient)
    print(patient_data)

    birth_date = patient_data.get("BirthDate", "N/A")
    if birth_date != "N/A":
        birth_date_obj = datetime.fromisoformat(birth_date)
        birth_date_formatted = birth_date_obj.strftime("%Y-%m-%d")
    else:
        birth_date_formatted = "N/A"

    patient_info = [
        {"name": "Nombre", "value": patient_data.get("Name")},
        {"name": "RUT", "value": patient_data.get("RUT")},
        {"name": "Email", "value": patient_data.get("Email")},
        {"name": "Celular", "value": patient_data.get("Phone")},
        {"name": "Fecha de Nacimiento", "value": birth_date_formatted},
        {"name": "Edad", "value": calculate_age(birth_date_obj)},
        # {"name": "Estado Civil", "value": patient_data.get("CivilState")},
    ]

    context = {
        "title": "Información General del Paciente",
        "table_data": patient_info,
    }

    html += render_template("template_report.html", context)
    return html


def render_template(template_file, context):
    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template(template_file)
    return template.render(context)


def generate_pdf(html_content, pdf_file, css_path=None):
    # config = pdfkit.configuration(
    #    wkhtmltopdf="C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe"
    # )

    options = {
        "quiet": "",
        "enable-local-file-access": "",
        "header-html": "header.html",
        "footer-html": "footer.html",
    }
    # pdfkit.from_string(
    #        html_content, pdf_file, configuration=config, options=options, css=css_path
    #    )
    try:
        pdfkit.from_string(html_content, pdf_file, options=options, css=css_path)
    except IOError as e:
        print(e)


def generate_pdf_to_byte_array(html_content):
    config = pdfkit.configuration(
        wkhtmltopdf="C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe"
    )
    options = {
        "quiet": "",
        "enable-local-file-access": "",
        "header-html": "header.html",
        "footer-html": "footer.html",
    }
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
        pdf_file_path = tmpfile.name

    try:
        # Generate PDF and save to the temporary file
        pdfkit.from_string(
            html_content,
            pdf_file_path,
            configuration=config,
            options=options,
        )

        # Read the PDF content from the temporary file into a byte array
        with open(pdf_file_path, "rb") as pdf_file:
            pdf_content = pdf_file.read()

        # Clean up the temporary file
        os.remove(pdf_file_path)

        return pdf_content
    except IOError as e:
        print(e)
        # Clean up the temporary file in case of error
        os.remove(pdf_file_path)
        return None


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
            "timestamp_epoch": start_datetime,
        }
    return results
