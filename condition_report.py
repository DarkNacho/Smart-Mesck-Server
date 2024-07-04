from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
import io


def generate_pdf_report_condition(condition_data_array):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []

    # Define the title and style
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    report_title = Paragraph("Reporte de Condiciones", title_style)

    # Add the title to the story
    story.append(report_title)
    story.append(Spacer(1, 12))

    for condition_data in condition_data_array:
        # Agregar subtítulo con el display del code del recurso
        code_display = condition_data["code"]["coding"][0]["display"]
        code_system = condition_data["code"]["coding"][0]["system"]
        subtitle = Paragraph(
            f"<b>{code_display}</b> - Sistema: {code_system}", styles["Heading2"]
        )
        story.append(subtitle)
        story.append(Spacer(1, 12))

        # Condition details
        condition_info = [
            ["ID de Condición", Paragraph(condition_data["id"], styles["Normal"])],
            [
                "Última Actualización",
                Paragraph(condition_data["meta"]["lastUpdated"], styles["Normal"]),
            ],
            [
                "Estado Clínico",
                Paragraph(
                    condition_data["clinicalStatus"]["coding"][0]["code"],
                    styles["Normal"],
                ),
            ],
            [
                "Código",
                Paragraph(
                    condition_data["code"]["coding"][0]["display"], styles["Normal"]
                ),
            ],
            [
                "Paciente",
                Paragraph(condition_data["subject"]["display"], styles["Normal"]),
            ],
            [
                "Encuentro",
                Paragraph(condition_data["encounter"]["display"], styles["Normal"]),
            ],
            [
                "Registrador",
                Paragraph(condition_data["recorder"]["display"], styles["Normal"]),
            ],
            ["Notas", Paragraph(condition_data["note"][0]["text"], styles["Normal"])],
        ]

        # Create a table with the condition info
        condition_table = Table(condition_info, colWidths=[2 * inch, 4 * inch])
        condition_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )

        # Add the table to the story
        story.append(condition_table)
        story.append(Spacer(1, 12))

    # Build the PDF
    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()

    return pdf


# Example usage
condition_data_array = [
    {
        "resourceType": "Condition",
        "id": "150",
        "meta": {
            "versionId": "1",
            "lastUpdated": "2024-06-28T14:02:34.666+00:00",
            "source": "#0lOdVizYYJTQDBsB",
        },
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active",
                }
            ]
        },
        "code": {
            "coding": [
                {
                    "system": "http://clinicaltables.nlm.nih.gov/fhir/CodeSystem/hpo",
                    "code": "HP:0000819",
                    "display": "HP:0000819, Diabetes mellitus",
                }
            ]
        },
        "subject": {"reference": "Patient/5", "display": "Juan Carlos Bodoque "},
        "encounter": {
            "reference": "Encounter/111",
            "display": "Profesional: Ignacio Andrés Martínez -- 2024-05-27 12:28 - 12:58",
        },
        "recorder": {"reference": "Practitioner/1", "display": "Dr. John Doe"},
        "note": [{"text": "notas aqui"}],
    },
    {
        "resourceType": "Condition",
        "id": "151",
        "meta": {
            "versionId": "1",
            "lastUpdated": "2024-06-29T10:12:34.666+00:00",
            "source": "#1lPdVizYYJTQDBsC",
        },
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "resolved",
                }
            ]
        },
        "code": {
            "coding": [
                {
                    "system": "http://clinicaltables.nlm.nih.gov/fhir/CodeSystem/hpo",
                    "code": "HP:0001945",
                    "display": "HP:0001945, Hypertension",
                }
            ]
        },
        "subject": {"reference": "Patient/6", "display": "Ana Pérez"},
        "encounter": {
            "reference": "Encounter/112",
            "display": "Profesional: Laura González -- 2024-05-28 10:00 - 10:30",
        },
        "recorder": {"reference": "Practitioner/2", "display": "Dr. Jane Smith"},
        "note": [{"text": "Resolución completa sin complicaciones."}],
    },
]

pdf = generate_pdf_report_condition(condition_data_array)
with open("reporte_condiciones.pdf", "wb") as f:
    f.write(pdf)
