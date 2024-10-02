from datetime import datetime
import os
import pdfkit
from jinja2 import Environment, FileSystemLoader

# Datos estáticos para demostración
static_data = [
    {"id": "1", "name": "Static Name 1", "value": "Static Value 1 sdasdasdasdada"},
    {"id": "2", "name": "Static Name 2", "value": "Static Value 2 nayasta"},
    {"id": "3", "name": "Static Name 3", "value": "Static Value 3"},
]


def observation_report(observations):
    html = ""
    for observation_data in observations:
        # Convertir la cadena de fecha a un objeto datetime
        fecha_objeto = datetime.fromisoformat(
            observation_data.get("meta", {}).get("lastUpdated", "1900-01-01T00:00:00")
        )
        fecha_formateada = fecha_objeto.strftime("%Y-%m-%d %H:%M:%S")

        # Agregar subtítulo con el display del code del recurso
        code_display = (
            observation_data.get("code", {})
            .get("coding", [{}])[0]
            .get("display", "N/A")
        )
        code_system = (
            observation_data.get("code", {}).get("coding", [{}])[0].get("system", "N/A")
        )
        subtitle = {
            "name": f"<b>{code_display}</b> - Sistema: {code_system}",
            "value": "",
            "style": "Heading2",
        }

        observation_info = [
            {
                "name": "ID de Observación",
                "value": observation_data.get("id", "N/A"),
                "style": "Normal",
            },
            {
                "name": "Última Actualización",
                "value": fecha_formateada,
                "style": "Normal",
            },
            {
                "name": "Estado",
                "value": observation_data.get("status", "N/A"),
                "style": "Normal",
            },
            {
                "name": "Categoría",
                "value": observation_data.get("category", [{}])[0]
                .get("coding", [{}])[0]
                .get("display", "N/A"),
                "style": "Normal",
            },
            {
                "name": "Código",
                "value": observation_data.get("code", {})
                .get("coding", [{}])[0]
                .get("code", "N/A"),
                "style": "Normal",
            },
            {
                "name": "Encuentro",
                "value": observation_data.get("encounter", {}).get("display", "N/A"),
                "style": "Normal",
            },
            {
                "name": "Emitido el",
                "value": observation_data.get("issued", "N/A"),
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
            {
                "name": "Interpretación",
                "value": ", ".join(
                    [
                        f"{code.get('display', 'N/A')} (Código: {code.get('code', 'N/A')})"
                        for code in observation_data.get("interpretation", [{}])[0].get(
                            "coding", []
                        )
                    ]
                ),
                "style": "Normal",
            },
            {
                "name": "Notas",
                "value": observation_data.get("note", [{}])[0].get("text", "N/A"),
                "style": "Normal",
            },
        ]

        context = {
            "title": code_display,
            "subtitle": subtitle,
            "table_data": observation_info,
        }

        html += render_template("template_report.html", context)

    return html


def render_template(template_file, context):
    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template(template_file)
    return template.render(context)


def generate_pdf(html_content, pdf_file, css_path=None):
    config = pdfkit.configuration(
        wkhtmltopdf="C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe"
    )
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


context = {
    "title": "My Titulo",
    "subtitle": "My Subtitulo",
    "table_data": static_data,
}


html_content = render_template("template_report.html", context)


generate_pdf(
    html_content,
    "output.pdf",
)
