from report.report_utils import render_template
from dateutil.parser import isoparse
import os


def clinical_impression_report(clinical_impression_data_array):
    context_title = {
        "title": "Reporte Impresiones Clínicas",
        "img_path": os.path.abspath("report/static/icon_clinical_impression.png"),
    }

    html = render_template("template_title.html", context_title)

    for clinical_impression_data in clinical_impression_data_array:
        # Convert the date strings to datetime objects
        last_updated = clinical_impression_data.get("meta", {}).get(
            "lastUpdated", "N/A"
        )
        if last_updated != "N/A":
            last_updated_obj = isoparse(last_updated)
            last_updated_formatted = last_updated_obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            last_updated_formatted = "N/A"

        date = clinical_impression_data.get("date", "N/A")
        if date != "N/A":
            date_obj = isoparse(date)
            date_formatted = date_obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            date_formatted = "N/A"

        # Extract relevant information
        status = clinical_impression_data.get("status", "N/A")
        description = clinical_impression_data.get("description", "N/A")
        subject = clinical_impression_data.get("subject", {}).get("display", "N/A")
        encounter = clinical_impression_data.get("encounter", {}).get("display", "N/A")
        assessor = clinical_impression_data.get("assessor", {}).get("display", "N/A")
        summary = clinical_impression_data.get("summary", "N/A")

        clinical_impression_info = [
            {
                "name": "Última Actualización",
                "value": last_updated_formatted,
                "style": "Normal",
            },
            {"name": "Fecha", "value": date_formatted, "style": "Normal"},
            {"name": "Estado", "value": status, "style": "Normal"},
            # {"name": "Descripción", "value": description, "style": "Normal"},
            {"name": "Paciente", "value": subject, "style": "Normal"},
            {"name": "Encuentro", "value": encounter, "style": "Normal"},
            {"name": "Evaluador", "value": assessor, "style": "Normal"},
            {"name": "Resumen", "value": summary, "style": "Normal"},
        ]

        context = {
            "title": f"{description}",
            "table_data": clinical_impression_info,
        }

        html += render_template("template_report.html", context)

    return html
