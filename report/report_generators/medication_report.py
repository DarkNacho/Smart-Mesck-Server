from report.report_utils import render_template
from dateutil.parser import isoparse
import os


def medication_report(medication_data_array):
    context_title = {
        "title": "Reporte Medicamentos",
        "img_path": os.path.abspath("report/static/icon_med.png"),
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
            # {
            #    "name": "Dosificación",
            #    "value": f"{dosage_text}, Ruta: {dosage_route}, Frecuencia: {dosage_frequency}, Cantidad: {dosage_amount}",
            #    "style": "Normal",
            # },
        ]

        context = {
            "title": code_display,
            "subtitle": f"System: {code_system} - Code: {code}",
            "table_data": medication_info,
        }

        html += render_template("template_report.html", context)

    return html
