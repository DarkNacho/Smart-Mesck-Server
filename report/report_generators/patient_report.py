from datetime import datetime
from utils import parse_patient_info
from report.report_utils import render_template
from dateutil.parser import isoparse
import os


def calculate_age(birthdate: datetime):
    today = datetime.today()
    age = (
        today.year
        - birthdate.year
        - ((today.month, today.day) < (birthdate.month, birthdate.day))
    )
    return age


def patient_report(patient):
    context_title = {
        "title": "Reporte Paciente",
        "img_path": os.path.abspath("report/static/icon_user.png"),
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
