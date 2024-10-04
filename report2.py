import logging

from datetime import datetime
import statistics
from dateutil.parser import isoparse
import io
import os
from fastapi.responses import StreamingResponse
import pdfkit
from jinja2 import Environment, FileSystemLoader
import tempfile


from typing import Annotated, Dict, List, Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

import httpx

from sqlalchemy import func
from sqlalchemy.orm import aliased
from sqlmodel import Session


from auth import isAuthorized as Authorized, isAuthorizedToken as AuthorizedToken


from database import get_session
from models import SensorData


router = APIRouter(prefix="/report", tags=["report"])

db_dependency = Annotated[Session, Depends(get_session)]
isAuthorized = Annotated[Authorized, Depends(Authorized)]
isAuthorizedToken = Annotated[AuthorizedToken, Depends(AuthorizedToken)]

HAPI_FHIR_URL = os.getenv("HAPI_FHIR_URL")


logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


@router.get(
    "/{patient_id}",
    summary="Generate a patient report",
    description="Generates a report for a patient based on various parameters.",
)
async def generate_patient_report(
    patient_id: str,
    token: isAuthorizedToken,
    db: db_dependency,
    obs: bool = Query(False, description="Include observations"),
    med: bool = Query(False, description="Include medications"),
    cond: bool = Query(False, description="Include conditions"),
    sensor: bool = Query(False, description="Include sensor data"),
    excluded_sensor_types: Optional[List[str]] = Query(
        None, description="Excluded sensor types"
    ),
    encounter_id: Optional[str] = Query(None, description="Encounter ID"),
    start: Optional[datetime] = Query(
        None, description="Minimum time in ISO format (e.g., 2023-10-01T12:00:00.000Z)"
    ),
    end: Optional[datetime] = Query(
        None, description="Maximum time in ISO format (e.g., 2023-10-02T12:00:00.000Z)"
    ),
):
    try:
        logging.debug(f"Generating report for patient_id: {patient_id}")

        patient = await fetch_resource("Patient", patient_id, token)

        logging.debug(f"Fetched patient data: {patient}")

        observations_data = []
        medication_data = []
        sensor_data = []
        condition_data = []

        params = {"patient": patient_id}
        if encounter_id:
            params["encounter"] = encounter_id

        if obs:
            data = await fetch_resources("Observation", params, token)
            observations_data = [item["resource"] for item in data.get("entry", [])]
            logging.debug(f"Fetched observations data")

        if cond:
            data = await fetch_resources("Condition", params, token)
            condition_data = [item["resource"] for item in data.get("entry", [])]
            logging.debug(f"Fetched condition data")

        if sensor:
            # TODO: hacer una get sensor_data para sólo un encuentro (que muestre los datos de ese sensor y no sólo el promedio)
            # sensor_data = await get_sensor_data(patient_id, db, encounter_id)
            sensor_data = await get_sensor_data_by_patient(
                patient_id, db, encounter_id, start, end, excluded_sensor_types
            )
            logging.debug(f"Fetched sensor data, length: {len(sensor_data)}")

        if med and not encounter_id:
            data = await fetch_resources("MedicationStatement", params, token)
            medication_data = [item["resource"] for item in data.get("entry", [])]
            logging.debug(f"Fetched medication data: {medication_data}")

        pdf_file = generate_report(
            patient_data=patient,
            observation_data_array=observations_data,
            sensor_data=sensor_data,
            medication_data_array=medication_data,
            condition_data_array=condition_data,
        )

        logging.debug("Generated PDF report")

        patient_info = parse_patient_info(patient)
        patient_name = patient_info.get("Name").replace(" ", "_")
        patient_rut = patient_info.get("RUT")

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
            headers={
                "Content-Disposition": f"attachment; filename={patient_rut}_{patient_name}_reporte.pdf"
            },
        )
    except Exception as e:
        logging.error(f"Error generating report for patient_id {patient_id}: {e}")

        raise HTTPException(status_code=500, detail="Error al generar el reporte")


import matplotlib.pyplot as plt
import matplotlib.dates as mdates
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
        html_data += sensor_summary_report(sensor_data)
        # story.extend(sensor_story)

    return generate_pdf_to_byte_array(html_data)


def custom_date_formatter(x, pos):
    return x.strftime("%Y-%m-%d %H:%M:%S.%f")[
        :-3
    ]  # Remove last 3 digits of microseconds to show milliseconds


def sensor_summary_report(data):

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
            # "Day",
            "Start",
            "End",
            "Duration",
        ]

        for sensor_type, sensor_data in encounter_data.items():
            sensorData[sensor_type]["min"].append(sensor_data["min"])
            sensorData[sensor_type]["max"].append(sensor_data["max"])
            sensorData[sensor_type]["avg"].append(sensor_data["avg"])
            sensorData[sensor_type]["timestamp_epoch"].append(sensor_data["start"])
            sensorData[sensor_type]["timestamps"].extend(sensor_data["timestamps"])
            sensorData[sensor_type]["values"].extend(sensor_data["values"])

            row = [{"value": sensor_type}]
            row.extend(
                [
                    {"value": sensor_data["min"]},
                    {"value": sensor_data["max"]},
                    {"value": sensor_data["avg"]},
                    {"value": sensor_data["count"]},
                    # {"value": sensor_data["day"]},
                    {"value": sensor_data["start"]},
                    {"value": sensor_data["end"]},
                    {"value": sensor_data["duration"]},
                ]
            )
        # quizás obtener el encuentro usando encounter_id y dar una info de por ejemplo que Profesional atendio
        context = {
            "title": f"{sensor_data['day']} - Encuentro {encounter_id}",
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
        ## Graph de todos los valores
        plt.figure()
        plt.plot(stats["timestamps"], stats["values"])
        plt.xlabel("Hora")
        plt.ylabel("Valor")
        plt.legend()
        plt.tight_layout()

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png")
        plt.close()
        img_buffer.seek(0)
        img_data = base64.b64encode(img_buffer.getvalue()).decode("utf-8")

        context_graph = {
            "title": f"{sensor_type} en el tiempo",
            "img_path": os.path.abspath("icon_graph.png"),
            "img_data": img_data,
        }
        html += render_template("template_graph.html", context_graph)

        if len(data) == 1:
            continue

        ## Sumarry Graph

        plt.figure()
        plt.plot(stats["timestamp_epoch"], stats["min"], label="Min", marker="o")
        plt.plot(stats["timestamp_epoch"], stats["max"], label="Max", marker="o")
        plt.plot(stats["timestamp_epoch"], stats["avg"], label="Avg", marker="o")
        # plt.title(f"{sensor_type} Sensor Data")
        plt.xlabel("Día")
        plt.ylabel("Valor")
        plt.legend()
        plt.tight_layout()

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png")
        plt.close()
        img_buffer.seek(0)
        img_data = base64.b64encode(img_buffer.getvalue()).decode("utf-8")

        context_graph = {
            "title": f"{sensor_type} Estadísticas",
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
            last_updated_obj = isoparse(last_updated)
            last_updated_formatted = last_updated_obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            last_updated_formatted = "N/A"

        # Formatear effectivePeriod start
        effective_start = medication_data.get("effectivePeriod", {}).get("start", "N/A")
        if effective_start != "N/A":
            effective_start_obj = isoparse(effective_start)
            effective_start_formatted = effective_start_obj.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        else:
            effective_start_formatted = "N/A"

        # Formatear effectivePeriod end
        effective_end = medication_data.get("effectivePeriod", {}).get("end", "N/A")
        if effective_end != "N/A":
            effective_end_obj = isoparse(effective_end)
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
        fecha_objeto = isoparse(
            observation_data.get("meta", {}).get("lastUpdated", "1900-01-01T00:00:00")
        )
        fecha_formateada = fecha_objeto.strftime("%Y-%m-%d %H:%M:%S")

        issued_value = observation_data.get("issued", "N/A")
        if issued_value != "N/A":
            issued_objeto = isoparse(issued_value)
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
        fecha_objeto = isoparse(
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
        birth_date_obj = isoparse(birth_date)
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
    # config = pdfkit.configuration(wkhtmltopdf="/usr/bin/wkhtmltopdf")
    config = None
    options = {
        "quiet": "",
        "enable-local-file-access": "",
        "header-html": "header.html",
        "footer-html": "footer.html",
    }
    try:
        pdfkit.from_string(
            html_content, pdf_file, configuration=config, options=options, css=css_path
        )
    except IOError as e:
        print(e)


def generate_pdf_to_byte_array(html_content):
    # config = pdfkit.configuration(
    #    wkhtmltopdf="C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe"
    # )
    # config = pdfkit.configuration(wkhtmltopdf="/usr/bin/wkhtmltopdf")
    config = None
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


async def get_sensor_data(
    patient_id: str,
    db: db_dependency,
    encounter_id: Optional[str] = None,
):

    # Subconsulta para obtener los valores y timestamps de cada tipo de sensor
    subquery = db.query(
        SensorData.sensor_type, SensorData.value, SensorData.timestamp_epoch
    ).filter(SensorData.patient_id == patient_id)

    if encounter_id:
        subquery = subquery.filter(SensorData.encounter_id == encounter_id)

    # Alias para la subconsulta
    subquery_alias = aliased(subquery.subquery())

    query = db.query(
        SensorData.encounter_id,
        SensorData.sensor_type,
        func.min(SensorData.value).label("min_value"),
        func.max(SensorData.value).label("max_value"),
        func.avg(SensorData.value).label("avg_value"),
        func.min(SensorData.timestamp_epoch).label("start_time"),
        func.max(SensorData.timestamp_epoch).label("end_time"),
        func.array_agg(subquery_alias.c.value).label("values_list"),
        func.array_agg(subquery_alias.c.timestamp_epoch).label("timestamps_list"),
    ).filter(SensorData.patient_id == patient_id)

    if encounter_id:
        query = query.filter(SensorData.encounter_id == encounter_id)

    query = query.join(
        subquery_alias, SensorData.sensor_type == subquery_alias.c.sensor_type
    )

    # test_res = query.all()
    query_result = query.group_by(SensorData.encounter_id, SensorData.sensor_type).all()

    # Preparing the results to return
    results = defaultdict(lambda: defaultdict(dict))
    for (
        encounter_id,
        sensor_type,
        min_value,
        max_value,
        avg_value,
        start_time,
        end_time,
        values,
        timestamps,
    ) in query_result:
        start_datetime = datetime.fromtimestamp(start_time)
        end_datetime = datetime.fromtimestamp(end_time)
        duration = end_datetime - start_datetime
        timestamps_datetime = [datetime.fromtimestamp(ts) for ts in timestamps]

        results[encounter_id][sensor_type] = {
            "min": round(min_value, 2),
            "max": round(max_value, 2),
            "avg": round(avg_value, 2),
            "count": len(values),
            "day": start_datetime.strftime("%d-%m-%Y"),
            "start": start_datetime.strftime("%H:%M:%S"),
            "end": end_datetime.strftime("%H:%M:%S"),
            "duration": str(duration).split(".")[0],  # Format duration to HH:MM:SS
            "timestamp_epoch": start_datetime,
            "values": values,
            "timestamps": timestamps_datetime,
        }
    return results


async def get_sensor_data_by_patient(
    patient_id: str,
    db,
    encounter_id: Optional[str] = None,
    min_time: Optional[datetime] = None,
    max_time: Optional[datetime] = None,
    excluded_sensor_types: Optional[List[str]] = None,
):
    # Query to get values and timestamps for each sensor type
    query = db.query(
        SensorData.encounter_id,
        SensorData.sensor_type,
        SensorData.value,
        SensorData.timestamp_epoch,
        SensorData.timestamp_millis,
    ).filter(SensorData.patient_id == patient_id)

    if encounter_id:
        query = query.filter(SensorData.encounter_id == encounter_id)

    if excluded_sensor_types:
        query = query.filter(SensorData.sensor_type.notin_(excluded_sensor_types))

    if min_time:
        min_timestamp = int(min_time.timestamp())
        query = query.filter(SensorData.timestamp_epoch >= min_timestamp)

    if max_time:
        max_timestamp = int(max_time.timestamp())
        query = query.filter(SensorData.timestamp_epoch <= max_timestamp)

    query_result = query.all()

    grouped_results = defaultdict(
        lambda: defaultdict(lambda: {"values": [], "timestamps": []})
    )
    for record in query_result:
        encounter_id = record.encounter_id
        sensor_type = record.sensor_type
        value = record.value
        timestamp = datetime.fromtimestamp(
            record.timestamp_epoch + record.timestamp_millis / 1000.0
        )

        grouped_results[encounter_id][sensor_type]["values"].append(value)
        grouped_results[encounter_id][sensor_type]["timestamps"].append(timestamp)

    # Calculate min, max, and avg for each sensor type within each encounter_id
    for encounter_id, sensor_data in grouped_results.items():
        for sensor_type, data in sensor_data.items():
            values = data["values"]
            if values:
                data["min"] = min(values)
                data["max"] = max(values)
                data["avg"] = statistics.mean(values)
                data["count"] = len(values)
                data["start"] = min(data["timestamps"])
                data["end"] = max(data["timestamps"])
                data["duration"] = str(data["end"] - data["start"]).split(".")[0]

                # Convert start and end to datetime objects if they are not already
                if isinstance(data["start"], str):
                    data["start"] = datetime.strptime(data["start"], "%H:%M:%S")
                if isinstance(data["end"], str):
                    data["end"] = datetime.strptime(data["end"], "%H:%M:%S")

                data["start_str"] = data["start"].strftime("%H:%M:%S")
                data["end_str"] = data["end"].strftime("%H:%M:%S")
                data["timestamp_epoch"] = int(data["start"].timestamp())
                data["day"] = data["start"].strftime("%d-%m-%Y")

    # Format the results to return
    grouped_results = {
        encounter_id: dict(sensor_data)
        for encounter_id, sensor_data in grouped_results.items()
    }
    return grouped_results
