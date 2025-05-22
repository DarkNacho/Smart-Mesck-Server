import os
from typing import Annotated, List, Optional
import httpx
from fastapi import Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session
from sqlalchemy.orm import aliased
from collections import defaultdict
from datetime import datetime
from database import get_session
from models import SensorData

import pdfkit
import tempfile
from jinja2 import Environment, FileSystemLoader
import PyPDF2
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io

import statistics

from utils import fetch_resource, fetch_resources


HAPI_FHIR_URL = os.getenv("HAPI_FHIR_URL")

db_dependency = Annotated[Session, Depends(get_session)]


def render_template(template_file, context):
    env = Environment(loader=FileSystemLoader("report/templates"))
    # env = Environment(loader=FileSystemLoader("."))
    template = env.get_template(template_file)
    return template.render(context)


def generate_pdf_to_byte_array(html_content, add_watermark=True):
    """
    Generates a PDF from HTML content and returns it as a byte array.

    Args:
        html_content (str): The HTML content to convert to PDF.
        add_watermark (bool): Whether to add a watermark to the PDF. Default is True.

    Returns:
        bytes: The PDF content as a byte array, or None if an error occurs.
    """
    # config = pdfkit.configuration(
    #    wkhtmltopdf="C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe"
    # )
    # config = pdfkit.configuration(wkhtmltopdf="/usr/bin/wkhtmltopdf")
    config = None

    options = {
        "quiet": "",
        "enable-local-file-access": "",
        "header-html": "report/templates/header.html",
        "footer-html": "report/templates/footer.html",
        "footer-right": "Página [page] de [topage]",  # Add pagination in footer right
        "footer-font-size": "9",
        "footer-line": True,  # Add a line above the footer
        "margin-bottom": "20mm",
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
            verbose=True,
        )

        if add_watermark:
            # Add watermark to the PDF
            watermarked_pdf_path = add_watermark_to_pdf(
                pdf_file_path, "report/static/logo.png"
            )

            # Read the watermarked PDF content into a byte array
            with open(watermarked_pdf_path, "rb") as pdf_file:
                pdf_content = pdf_file.read()

            # Clean up the temporary files
            os.remove(pdf_file_path)
            os.remove(watermarked_pdf_path)
        else:
            # Read the original PDF content into a byte array
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


def add_watermark_to_pdf(input_pdf_path, watermark_image_path):
    """
    Adds an image watermark to every page of the input PDF.

    Args:
        input_pdf_path (str): Path to the input PDF.
        watermark_image_path (str): Path to the watermark image.

    Returns:
        str: Path to the watermarked PDF.
    """
    # Create a temporary file for the watermarked PDF
    with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
        watermarked_pdf_path = tmpfile.name

    # Read the input PDF
    with open(input_pdf_path, "rb") as input_pdf:
        pdf_reader = PyPDF2.PdfReader(input_pdf)
        pdf_writer = PyPDF2.PdfWriter()

        for page in pdf_reader.pages:
            # Create a watermark PDF with the image
            watermark_pdf = create_watermark_pdf(
                watermark_image_path, page.mediabox.width, page.mediabox.height
            )

            # Merge the watermark with the current page
            page.merge_page(watermark_pdf.pages[0])
            pdf_writer.add_page(page)

        # Write the watermarked PDF to the temporary file
        with open(watermarked_pdf_path, "wb") as output_pdf:
            pdf_writer.write(output_pdf)

    return watermarked_pdf_path


def create_watermark_pdf(image_path, page_width, page_height):
    """
    Creates a PDF containing the watermark image with transparency and diagonal positioning.

    Args:
        image_path (str): Path to the watermark image.
        page_width (float): Width of the page.
        page_height (float): Height of the page.

    Returns:
        PyPDF2.PdfReader: A PDF reader object containing the watermark.
    """
    # Convert page dimensions to float in case they are decimal.Decimal
    page_width = float(page_width)
    page_height = float(page_height)

    # Load the image to get its original dimensions
    from PIL import Image

    with Image.open(image_path) as img:
        img_width, img_height = img.size

    # Adjust the image size to fit the page while maintaining aspect ratio
    scale_factor = min(
        page_width / img_width, page_height / img_height, 0.5
    )  # Scale down to 50% max
    scaled_width = img_width * scale_factor
    scaled_height = img_height * scale_factor

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))

    # Set transparency
    can.saveState()
    can.setFillAlpha(
        0.1
    )  # Adjust transparency (0.0 = fully transparent, 1.0 = fully opaque)

    # Check if the image is too small; if so, repeat it with rotation
    if scaled_width < page_width / 2 or scaled_height < page_height / 2:
        x_offset = -scaled_width  # Start slightly off the page for diagonal effect
        y_offset = -scaled_height
        while y_offset < page_height + scaled_height:
            while x_offset < page_width + scaled_width:
                can.saveState()
                can.translate(x_offset + scaled_width / 2, y_offset + scaled_height / 2)
                can.rotate(45)  # Rotate 45 degrees
                can.drawImage(
                    image_path,
                    -scaled_width / 2,
                    -scaled_height / 2,
                    width=scaled_width,
                    height=scaled_height,
                    mask="auto",
                )
                can.restoreState()
                x_offset += scaled_width
            x_offset = -scaled_width
            y_offset += scaled_height
    else:
        # Center the image diagonally
        can.translate(
            page_width / 2, page_height / 2
        )  # Move origin to the center of the page
        can.rotate(45)  # Rotate 45 degrees
        can.drawImage(
            image_path,
            -scaled_width / 2,
            -scaled_height / 2,
            width=scaled_width,
            height=scaled_height,
            mask="auto",
        )

    can.restoreState()
    can.save()

    packet.seek(0)
    return PyPDF2.PdfReader(packet)


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


async def get_sensor_data_by_patient_and_sensor(
    patient_id: str,
    db,
    required_sensor_type: str,
    encounter_id: Optional[List[str]] = None,
):
    """
    Fetch sensor data for a specific patient and encounter, filtered by a required sensor type.

    Args:
        patient_id (str): The ID of the patient.
        db: The database session.
        required_sensor_type (str): The required sensor type to filter by.
        encounter_id (Optional[List[str]]): List of encounter IDs to filter by.

    Returns:
        dict: Grouped sensor data by encounter and sensor type.
    """
    if not required_sensor_type:
        raise ValueError("The 'required_sensor_type' parameter is required.")

    # Query to get values and timestamps for each sensor type
    query = db.query(
        SensorData.encounter_id,
        SensorData.sensor_type,
        SensorData.value,
        SensorData.timestamp_epoch,
        SensorData.timestamp_millis,
    ).filter(SensorData.patient_id == patient_id)

    if encounter_id:
        query = query.filter(SensorData.encounter_id.in_(encounter_id))

    # Filter by the required sensor type
    query = query.filter(SensorData.sensor_type == required_sensor_type)

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


async def get_historical_sensor_summary_by_patient(
    patient_id: str,
    db,
    min_time: Optional[datetime] = None,
    max_time: Optional[datetime] = None,
):
    """
    Obtiene un resumen histórico general de los valores más relevantes de cada sensor para un paciente.
    Opcionalmente filtra por un rango de fechas.

    Args:
        patient_id (str): El ID del paciente.
        db: La sesión de la base de datos.
        min_time (Optional[datetime]): Fecha mínima para filtrar los datos (inclusive).
        max_time (Optional[datetime]): Fecha máxima para filtrar los datos (inclusive).

    Returns:
        dict: Resumen de los valores más relevantes por sensor.
    """
    # Query para obtener los datos de los sensores
    query = db.query(
        SensorData.sensor_type,
        func.min(SensorData.value).label("min_value"),
        func.max(SensorData.value).label("max_value"),
        func.avg(SensorData.value).label("avg_value"),
        func.stddev(SensorData.value).label("stddev_value"),
        func.percentile_cont(0.5).within_group(SensorData.value).label("median_value"),
        func.count(SensorData.value).label("count"),
    ).filter(SensorData.patient_id == patient_id)

    # Aplicar filtros de tiempo si se proporcionan
    if min_time:
        min_timestamp = int(min_time.timestamp())
        query = query.filter(SensorData.timestamp_epoch >= min_timestamp)

    if max_time:
        max_timestamp = int(max_time.timestamp())
        query = query.filter(SensorData.timestamp_epoch <= max_timestamp)

    # Agrupar por tipo de sensor
    query = query.group_by(SensorData.sensor_type)

    # Ejecutar la consulta
    query_result = query.all()

    # Preparar los resultados
    summary_results = {}
    for record in query_result:
        sensor_type = record.sensor_type
        summary_results[sensor_type] = {
            "min": round(record.min_value, 2) if record.min_value is not None else None,
            "max": round(record.max_value, 2) if record.max_value is not None else None,
            "avg": round(record.avg_value, 2) if record.avg_value is not None else None,
            "median": (
                round(record.median_value, 2)
                if record.median_value is not None
                else None
            ),
            "stddev": (
                round(record.stddev_value, 2)
                if record.stddev_value is not None
                else None
            ),
            "count": record.count,
        }

    return summary_results


async def get_sensor_progress_over_time(
    patient_id: str,
    db,
    time_grouping: str = "week",
):
    """
    Obtiene el progreso en el tiempo para todas las variables disponibles.

    Args:
        patient_id (str): El ID del paciente.
        db: La sesión de la base de datos.
        time_grouping (str): Agrupación temporal ("week", "month", "day").

    Returns:
        dict: Progreso en el tiempo para cada sensor agrupado por tipo.
    """
    # Definir la agrupación temporal
    if time_grouping == "week":
        time_format = func.date_trunc(
            "week", func.to_timestamp(SensorData.timestamp_epoch)
        )
    elif time_grouping == "month":
        time_format = func.date_trunc(
            "month", func.to_timestamp(SensorData.timestamp_epoch)
        )
    elif time_grouping == "day":
        time_format = func.date_trunc(
            "day", func.to_timestamp(SensorData.timestamp_epoch)
        )
    else:
        raise ValueError(
            "El parámetro 'time_grouping' debe ser 'week', 'month' o 'day'."
        )

    # Query para obtener los datos de los sensores
    query = db.query(
        time_format.label("time_period"),
        SensorData.sensor_type,
        func.min(SensorData.value).label("min_value"),
        func.max(SensorData.value).label("max_value"),
        func.avg(SensorData.value).label("avg_value"),
        func.percentile_cont(0.5).within_group(SensorData.value).label("median_value"),
    ).filter(SensorData.patient_id == patient_id)

    # Agrupar por período de tiempo y tipo de sensor
    query = query.group_by(time_format, SensorData.sensor_type)

    # Ejecutar la consulta
    query_result = query.all()

    # Preparar los resultados
    progress_results = defaultdict(lambda: defaultdict(list))
    for record in query_result:
        time_period = record.time_period.strftime("%Y-%m-%d")
        sensor_type = record.sensor_type
        progress_results[sensor_type]["time_periods"].append(time_period)
        progress_results[sensor_type]["min_values"].append(record.min_value)
        progress_results[sensor_type]["max_values"].append(record.max_value)
        progress_results[sensor_type]["avg_values"].append(record.avg_value)
        progress_results[sensor_type]["median_values"].append(record.median_value)

    return progress_results


async def fetch_and_group_questionnaire_responses(params, token):
    data = await fetch_resources("QuestionnaireResponse", params, token)
    all_responses = [item["resource"] for item in data.get("entry", [])]
    grouped = defaultdict(list)
    for resp in all_responses:
        qid = resp.get("questionnaire", "")
        if "/" in qid:
            qid = qid.split("/")[-1]
        grouped[qid].append(resp)
    return grouped
