from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
import io

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
import io


def generate_pdf_report_medication(medication_data_array):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []

    # Define the title and style
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    report_title = Paragraph("Reporte de Medicaciones", title_style)

    # Add the title to the story
    story.append(report_title)
    story.append(Spacer(1, 12))

    for medication_data in medication_data_array:
        # Agregar subtítulo con el display del code del recurso
        code_display = medication_data["medicationCodeableConcept"]["coding"][0][
            "display"
        ]
        code_system = medication_data["medicationCodeableConcept"]["coding"][0][
            "system"
        ]
        subtitle = Paragraph(
            f"<b>{code_display}</b> - Sistema: {code_system}", styles["Heading2"]
        )
        story.append(subtitle)
        story.append(Spacer(1, 12))

        # Dosage details
        dosage_text = medication_data["dosage"][0]["text"]
        dosage_route = medication_data["dosage"][0]["route"]["coding"][0]["display"]
        dosage_frequency = f"{medication_data['dosage'][0]['timing']['repeat']['frequency']} vez/veces cada {medication_data['dosage'][0]['timing']['repeat']['period']} {medication_data['dosage'][0]['timing']['repeat']['periodUnit']}"
        dosage_amount = f"{medication_data['dosage'][0]['doseQuantity']['value']} {medication_data['dosage'][0]['doseQuantity']['unit']}"

        # Medication details
        medication_info = [
            ["ID de Medicación", Paragraph(medication_data["id"], styles["Normal"])],
            [
                "Última Actualización",
                Paragraph(medication_data["meta"]["lastUpdated"], styles["Normal"]),
            ],
            ["Estado", Paragraph(medication_data["status"], styles["Normal"])],
            ["Medicamento", Paragraph(code_display, styles["Normal"])],
            [
                "Paciente",
                Paragraph(medication_data["subject"]["display"], styles["Normal"]),
            ],
            [
                "Contexto",
                Paragraph(medication_data["context"]["display"], styles["Normal"]),
            ],
            [
                "Período Efectivo",
                Paragraph(
                    f"Desde: {medication_data['effectivePeriod']['start']} Hasta: {medication_data['effectivePeriod']['end']}",
                    styles["Normal"],
                ),
            ],
            [
                "Fuente de Información",
                Paragraph(
                    medication_data["informationSource"]["display"], styles["Normal"]
                ),
            ],
            [
                "Dosificación",
                Paragraph(
                    f"{dosage_text}\nRuta: {dosage_route}\nFrecuencia: {dosage_frequency}\nCantidad: {dosage_amount}",
                    styles["Normal"],
                ),
            ],
        ]

        # Create a table with the medication info
        medication_table = Table(medication_info, colWidths=[2 * inch, 4 * inch])
        medication_table.setStyle(
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
        story.append(medication_table)
        story.append(Spacer(1, 12))

    # Build the PDF
    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()

    return pdf


# Example usage
medication_data_array = [
    {
        "resourceType": "MedicationStatement",
        "id": "151",
        "meta": {
            "versionId": "1",
            "lastUpdated": "2024-06-28T14:09:40.652+00:00",
            "source": "#rLrXwusLbLjVlWB8",
        },
        "status": "active",
        "medicationCodeableConcept": {
            "coding": [
                {
                    "system": "http://clinicaltables.nlm.nih.gov/fhir/CodeSystem/rxterms",
                    "code": "EUTHYROX (Oral Pill)",
                    "display": "EUTHYROX (Oral Pill)",
                }
            ]
        },
        "subject": {"reference": "Patient/5", "display": "Juan Carlos Bodoque "},
        "context": {
            "reference": "Encounter/111",
            "display": "Profesional: Ignacio Andrés Martínez -- 2024-05-27 12:28 - 12:58",
        },
        "effectivePeriod": {
            "start": "2024-06-28T14:09:09.190Z",
            "end": "2024-07-05T14:09:09.190Z",
        },
        "informationSource": {"reference": "Practitioner/1", "display": "Dr. John Doe"},
        "dosage": [
            {
                "text": "Tomar 1 pastilla cada mañana",
                "timing": {"repeat": {"frequency": 1, "period": 1, "periodUnit": "d"}},
                "route": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v3-RouteOfAdministration",
                            "code": "PO",
                            "display": "Oral",
                        }
                    ]
                },
                "doseQuantity": {
                    "value": 1,
                    "unit": "pastilla",
                    "system": "http://unitsofmeasure.org",
                    "code": "tab",
                },
            }
        ],
    }
]

pdf = generate_pdf_report_medication(medication_data_array)
with open("reporte_medicaciones.pdf", "wb") as f:
    f.write(pdf)
