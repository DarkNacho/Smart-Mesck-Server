from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session
from typing import Annotated, List, Optional
import io

from auth import isAuthorized as Authorized, isAuthorizedToken as AuthorizedToken


from database import get_session


from report.report_utils import (
    fetch_resource,
    fetch_resources,
    parse_patient_info,
    get_sensor_data_by_patient,
)


from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session
from typing import Annotated, List, Optional
import io

from auth import isAuthorized as Authorized, isAuthorizedToken as AuthorizedToken
from database import get_session
from report.report_utils import (
    fetch_resource,
    fetch_resources,
    generate_pdf_to_byte_array,
    get_sensor_data_by_patient,
)
from report.report_generators.general_report import general_report
from report.report_generators.patient_report import patient_report
from report.report_generators.observation_report import observation_report
from report.report_generators.medication_report import medication_report
from report.report_generators.condition_report import condition_report
from report.report_generators.sensor_report import sensor_report
from report.report_generators.questionnaire_report import questionnaire_report


from report.report_generators.general_report import general_report

router = APIRouter(prefix="/report", tags=["report"])

db_dependency = Annotated[Session, Depends(get_session)]
isAuthorized = Annotated[Authorized, Depends(Authorized)]
isAuthorizedToken = Annotated[AuthorizedToken, Depends(AuthorizedToken)]


@router.get(
    "/{patient_id}",
    summary="Generate a patient report",
    description="Generates a report for a patient based on various parameters.",
)
async def generate_patient_report(
    patient_id: str,
    token: isAuthorizedToken,  # type: ignore
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
        print(f"Generating report for patient_id: {patient_id}")

        patient = await fetch_resource("Patient", patient_id, token)

        print(f"Fetched patient data: {patient.get('id')}")

        observations_data = []
        medication_data = []
        sensor_data = []
        condition_data = []
        clinical_impression_data = []

        params = {"patient": patient_id}
        if encounter_id:
            params["encounter"] = encounter_id

        if obs:
            # data = await fetch_resources("Observation", params, token)
            # observations_data = [item["resource"] for item in data.get("entry", [])]

            data = await fetch_resources(
                "ClinicalImpression", {"patient": patient_id}, token
            )
            clinical_impression_data = [
                item["resource"] for item in data.get("entry", [])
            ]
            print("data: clinical", data)
            print(f"Fetched observations/clinicalimpresion data")

        if cond:
            data = await fetch_resources("Condition", params, token)
            condition_data = [item["resource"] for item in data.get("entry", [])]
            print(f"Fetched condition data")

        if sensor:
            # TODO: hacer una get sensor_data para sólo un encuentro (que muestre los datos de ese sensor y no sólo el promedio)
            # sensor_data = await get_sensor_data(patient_id, db, encounter_id)
            sensor_data = await get_sensor_data_by_patient(
                patient_id, db, encounter_id, start, end, excluded_sensor_types
            )
            print(f"Fetched sensor data, length: {len(sensor_data)}")

        if med and not encounter_id:
            data = await fetch_resources("MedicationStatement", params, token)
            medication_data = [item["resource"] for item in data.get("entry", [])]
            print(f"Fetched medication data: {medication_data}")

        pdf_file = general_report(
            patient_data=patient,
            clinical_impression_data_array=clinical_impression_data,
            observation_data_array=observations_data,
            sensor_data=sensor_data,
            medication_data_array=medication_data,
            condition_data_array=condition_data,
        )

        print("Generated PDF report")

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
        print(f"Error generating report for patient_id {patient_id}: {e}")

        raise HTTPException(status_code=500, detail="Error al generar el reporte")


@router.get("/{patient_id}/observations", summary="Generate an observation report")
async def generate_observation_report(
    patient_id: str,
    token: isAuthorizedToken,  # type: ignore
):
    try:
        patient = await fetch_resource("Patient", patient_id, token)
        data = await fetch_resources("Observation", {"patient": patient_id}, token)
        observations_data = [item["resource"] for item in data.get("entry", [])]

        # Generate the observation report
        html_data = patient_report(patient)
        html_data += observation_report(observations_data)
        pdf_file = generate_pdf_to_byte_array(html_data)

        patient_info = parse_patient_info(patient)
        patient_name = patient_info.get("Name").replace(" ", "_")
        patient_rut = patient_info.get("RUT")

        return StreamingResponse(
            io.BytesIO(pdf_file),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={patient_rut}_{patient_name}_observations_report.pdf"
            },
        )
    except Exception as e:
        print(f"Error generating observation report for patient_id {patient_id}: {e}")
        raise HTTPException(status_code=500, detail="Error al generar el reporte")


@router.get("/{patient_id}/medications", summary="Generate a medication report")
async def generate_medication_report(
    patient_id: str,
    token: isAuthorizedToken,  # type: ignore
):
    try:
        patient = await fetch_resource("Patient", patient_id, token)
        data = await fetch_resources(
            "MedicationStatement", {"patient": patient_id}, token
        )
        medication_data = [item["resource"] for item in data.get("entry", [])]

        # Generate the medication report
        html_data = patient_report(patient)
        html_data += medication_report(medication_data)
        pdf_file = generate_pdf_to_byte_array(html_data)

        patient_info = parse_patient_info(patient)
        patient_name = patient_info.get("Name").replace(" ", "_")
        patient_rut = patient_info.get("RUT")

        return StreamingResponse(
            io.BytesIO(pdf_file),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={patient_rut}_{patient_name}_medication_report.pdf"
            },
        )
    except Exception as e:
        print(f"Error generating medication report for patient_id {patient_id}: {e}")
        raise HTTPException(status_code=500, detail="Error al generar el reporte")


@router.get("/{patient_id}/conditions", summary="Generate a condition report")
async def generate_condition_report(
    patient_id: str,
    token: isAuthorizedToken,  # type: ignore
):
    try:
        patient = await fetch_resource("Patient", patient_id, token)
        data = await fetch_resources("Condition", {"patient": patient_id}, token)
        condition_data = [item["resource"] for item in data.get("entry", [])]

        # Generate the condition report
        html_data = patient_report(patient)
        html_data += condition_report(condition_data)
        pdf_file = generate_pdf_to_byte_array(html_data)

        patient_info = parse_patient_info(patient)
        patient_name = patient_info.get("Name").replace(" ", "_")
        patient_rut = patient_info.get("RUT")

        return StreamingResponse(
            io.BytesIO(pdf_file),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={patient_rut}_{patient_name}_conditions_report.pdf"
            },
        )
    except Exception as e:
        print(f"Error generating condition report for patient_id {patient_id}: {e}")
        raise HTTPException(status_code=500, detail="Error al generar el reporte")


@router.get("/{patient_id}/sensors", summary="Generate a sensor report")
async def generate_sensor_report(
    patient_id: str,
    token: isAuthorizedToken,  # type: ignore
    db: db_dependency,
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
        patient = await fetch_resource("Patient", patient_id, token)
        sensor_data = await get_sensor_data_by_patient(
            patient_id, db, encounter_id, start, end, excluded_sensor_types
        )

        # Generate the sensor report
        html_data = patient_report(patient)
        html_data += sensor_report(sensor_data)
        pdf_file = generate_pdf_to_byte_array(html_data)

        patient_info = parse_patient_info(patient)
        patient_name = patient_info.get("Name").replace(" ", "_")
        patient_rut = patient_info.get("RUT")

        return StreamingResponse(
            io.BytesIO(pdf_file),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={patient_rut}_{patient_name}_sensors_report.pdf"
            },
        )
    except Exception as e:
        print(f"Error generating sensor report for patient_id {patient_id}: {e}")
        raise HTTPException(status_code=500, detail="Error al generar el reporte")


@router.get(
    "/questionnaire/{questionnaireResponse_id}/",
    summary="Generate a questionnaire report",
)
async def generate_questionnaire_report(
    questionnaireResponse_id: str,
    token: isAuthorizedToken,  # type: ignore
    include_bar_chart: bool = Query(
        False, description="Include bar chart in the report"
    ),
    include_pie_chart: bool = Query(
        False, description="Include pie chart in the report"
    ),
    include_line_chart: bool = Query(
        False, description="Include line chart in the report"
    ),
):
    try:
        questionnaire_response = await fetch_resource(
            "QuestionnaireResponse", questionnaireResponse_id, token
        )

        if not questionnaire_response:
            raise HTTPException(
                status_code=404, detail="QuestionnaireResponse not found"
            )

        questionnaire_id = questionnaire_response.get("questionnaire", {}).split("/")[
            -1
        ]
        if not questionnaire_id:
            raise HTTPException(
                status_code=400,
                detail="Questionnaire ID not found in QuestionnaireResponse",
            )

        questionnaire = await fetch_resource("Questionnaire", questionnaire_id, token)
        if not questionnaire:
            raise HTTPException(status_code=404, detail="Questionnaire not found")

        html_data = questionnaire_report(
            questionnaire_response=questionnaire_response,
            questionnaire=questionnaire,
            include_bar_chart=include_bar_chart,
            include_pie_chart=include_pie_chart,
            include_line_chart=include_line_chart,
        )

        pdf_file = generate_pdf_to_byte_array(html_data)

        questionnaire_name = questionnaire.get("title", "questionnaire").replace(
            " ", "_"
        )

        return StreamingResponse(
            io.BytesIO(pdf_file),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={questionnaire_name}_report.pdf"
            },
        )
    except Exception as e:
        print(
            f"Error generating questionnaire report for id {questionnaireResponse_id}: {e}"
        )
        raise HTTPException(status_code=500, detail="Error al generar el reporte")


@router.get(
    "/data/{patient_id}",
    summary="Get Sensor Data by Patient",
    description="Get sensor data for a patient based on various parameters.",
)
async def get_sensor_data_by_patient_endpoint(
    patient_id: str,
    db: db_dependency,
    encounter_id: Optional[str] = None,
    min_time: Optional[datetime] = None,
    max_time: Optional[datetime] = None,
    excluded_sensor_types: Optional[List[str]] = Query(None),
):
    return await get_sensor_data_by_patient(
        patient_id, db, encounter_id, min_time, max_time, excluded_sensor_types
    )
