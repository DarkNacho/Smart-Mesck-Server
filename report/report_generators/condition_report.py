from report.report_utils import render_template
from dateutil.parser import isoparse
import os


def condition_report(condition_data_array):
    context_title = {
        "title": "Reporte Condiciones",
        "img_path": os.path.abspath("report/static/icon_cond.png"),
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
