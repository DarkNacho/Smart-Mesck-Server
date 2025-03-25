from report.report_utils import render_template
from dateutil.parser import isoparse
import os


def observation_report(observations):
    context_title = {
        "title": "Reporte Observaciones",
        "img_path": os.path.abspath("report/static/icon_obs.png"),
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
