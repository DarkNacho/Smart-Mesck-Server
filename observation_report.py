from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
import io


def generate_pdf_report(observation_data_array):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []

    # Define the title and style
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    report_title = Paragraph("Reporte de Observaciones", title_style)

    # Add the title to the story
    story.append(report_title)
    story.append(Spacer(1, 12))

    for observation_data in observation_data_array:
        # Convertir la cadena de fecha a un objeto datetime
        fecha_objeto = datetime.fromisoformat(observation_data["meta"]["lastUpdated"])
        fecha_formateada = fecha_objeto.strftime("%Y-%m-%d %H:%M:%S")

        # Agregar subtítulo con el display del code del recurso
        code_display = observation_data["code"]["coding"][0]["display"]
        code_system = observation_data["code"]["coding"][0]["system"]
        subtitle = Paragraph(
            f"<b>{code_display}</b> - Sistema: {code_system}", styles["Heading2"]
        )
        story.append(subtitle)
        story.append(Spacer(1, 12))

        observation_info = [
            ["ID de Observación", Paragraph(observation_data["id"], styles["Normal"])],
            ["Última Actualización", Paragraph(fecha_formateada, styles["Normal"])],
            ["Estado", Paragraph(observation_data["status"], styles["Normal"])],
            [
                "Categoría",
                Paragraph(
                    observation_data["category"][0]["coding"][0]["display"],
                    styles["Normal"],
                ),
            ],
            [
                "Código",
                Paragraph(
                    observation_data["code"]["coding"][0]["code"], styles["Normal"]
                ),
            ],
            [
                "Paciente",
                Paragraph(
                    f"{observation_data['subject']['display']}", styles["Normal"]
                ),
            ],
            [
                "Encuentro",
                Paragraph(
                    f"{observation_data['encounter']['display']}", styles["Normal"]
                ),
            ],
            ["Emitido el", Paragraph(observation_data["issued"], styles["Normal"])],
            [
                "Performer",
                Paragraph(
                    f"{observation_data['performer'][0]['display']}", styles["Normal"]
                ),
            ],
            ["Valor", Paragraph(observation_data["valueString"], styles["Normal"])],
            [
                "Interpretación",
                Paragraph(
                    ", ".join(
                        [
                            f"{code['display']} (Código: {code['code']})"
                            for code in observation_data["interpretation"][0]["coding"]
                        ]
                    ),
                    styles["Normal"],
                ),
            ],
            ["Notas", Paragraph(observation_data["note"][0]["text"], styles["Normal"])],
        ]

        # Create a table with the observation info
        observation_table = Table(observation_info, colWidths=[2 * inch, 4 * inch])
        observation_table.setStyle(
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
        story.append(observation_table)
        story.append(Spacer(1, 12))

    # Build the PDF
    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()

    return pdf


# Example usage
observation_data_array = [
    {
        "resourceType": "Observation",
        "id": "104",
        "meta": {
            "versionId": "2",
            "lastUpdated": "2024-05-14T21:46:14.638+00:00",
            "source": "#McBXsMymRdbiGLHt",
        },
        "status": "unknown",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "procedure",
                        "display": "Procedimiento",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "18690-8",
                    "display": "Body weight",
                }
            ]
        },
        "subject": {"reference": "Patient/5", "display": "Juan Carlos Bodoque"},
        "encounter": {
            "reference": "Encounter/6",
            "display": "Profesional: Ignacio Martínez -- 2024-05-14 15:02 - 15:32",
        },
        "issued": "2024-05-14T21:42:57.408Z",
        "performer": [{"reference": "Practitioner/3", "display": "Ignacio Martínez"}],
        "valueString": "120 kg",
        "interpretation": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": "N",
                        "display": "Normal",
                    },
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": "W",
                        "display": "Peor",
                    },
                ]
            }
        ],
        "note": [{"text": "prueba nota 666"}],
    },
    {
        "resourceType": "Observation",
        "id": "105",
        "meta": {
            "versionId": "1",
            "lastUpdated": "2024-05-15T15:46:14.638+00:00",
            "source": "#KcBXsMymRdbiGLHu",
        },
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Signos vitales",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "29463-7",
                    "display": "Body weight",
                }
            ]
        },
        "subject": {"reference": "Patient/6", "display": "Ana Pérez"},
        "encounter": {
            "reference": "Encounter/7",
            "display": "Profesional: Laura González -- 2024-05-15 14:00 - 14:30",
        },
        "issued": "2024-05-15T15:42:57.408Z",
        "performer": [{"reference": "Practitioner/4", "display": "Laura González"}],
        "valueString": "65 kg",
        "interpretation": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": "N",
                        "display": "Normal",
                    }
                ]
            }
        ],
        "note": [{"text": "prueba nota 123"}],
    },
]

pdf = generate_pdf_report(observation_data_array)
with open("reporte_observaciones.pdf", "wb") as f:
    f.write(pdf)
