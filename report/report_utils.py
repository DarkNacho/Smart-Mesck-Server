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


HAPI_FHIR_URL = os.getenv("HAPI_FHIR_URL")

db_dependency = Annotated[Session, Depends(get_session)]


def render_template(template_file, context):
    env = Environment(loader=FileSystemLoader("report/templates"))
    # env = Environment(loader=FileSystemLoader("."))
    template = env.get_template(template_file)
    return template.render(context)


def generate_pdf_to_byte_array(html_content):
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

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))

    # Set transparency
    can.saveState()
    can.setFillAlpha(
        0.2
    )  # Adjust transparency (0.0 = fully transparent, 1.0 = fully opaque)

    # Rotate the canvas for diagonal positioning
    can.translate(
        page_width / 2, page_height / 2
    )  # Move origin to the center of the page
    can.rotate(45)  # Rotate 45 degrees (diagonal)
    can.drawImage(
        image_path,
        -page_width / 2,
        -page_height / 2,
        width=page_width,
        height=page_height,
        mask="auto",
    )

    can.restoreState()
    can.save()

    packet.seek(0)
    return PyPDF2.PdfReader(packet)


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

    print(f"Fetching {url}")

    async with httpx.AsyncClient(timeout=50.0) as client:
        response = await client.get(url, headers=headers)

    if response.status_code != 200:
        response_data = response.json()
        diagnostic_message = "Failed to fetch {url}\n"
        diagnostic_message += response_data.get("issue", [{}])[0].get(
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

    print(f"Fetching {url} with params: {params}")

    async with httpx.AsyncClient(timeout=50.0, params=params) as client:
        response = await client.get(url, headers=headers)

    if response.status_code != 200:
        response_data = response.json()
        diagnostic_message = f"Failed to fetch {url}\n"
        diagnostic_message += response_data.get("issue", [{}])[0].get(
            "diagnostics", "Unknown error"
        )
        raise HTTPException(status_code=response.status_code, detail=diagnostic_message)

    return response.json()


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
