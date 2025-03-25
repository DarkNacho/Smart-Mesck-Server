from report.report_utils import render_template
from dateutil.parser import isoparse

from report.report_utils import generate_pdf_to_byte_array
from report.report_generators.patient_report import patient_report
from report.report_generators.clinical_impression_report import (
    clinical_impression_report,
)
from report.report_generators.condition_report import condition_report
from report.report_generators.observation_report import observation_report
from report.report_generators.medication_report import medication_report
from report.report_generators.sensor_report import sensor_report


def general_report(
    patient_data,
    clinical_impression_data_array=None,
    condition_data_array=None,
    observation_data_array=None,
    medication_data_array=None,
    sensor_data=None,
):

    html_data = patient_report(patient_data)

    # Add the clinical impressions to the story if provided
    if (
        clinical_impression_data_array is not None
        and len(clinical_impression_data_array) > 0
    ):
        print("generating clinical impression report")
        html_data += clinical_impression_report(clinical_impression_data_array)

    # Add the conditions to the story if provided
    if condition_data_array is not None and len(condition_data_array) > 0:
        print("generating condition report")
        html_data += condition_report(condition_data_array)

    # Add the observations to the story if provided
    if observation_data_array is not None and len(observation_data_array) > 0:
        print("generating observation report")
        html_data += observation_report(observation_data_array)

    # Add the medications to the story if provided
    if medication_data_array is not None and len(medication_data_array) > 0:
        print("generating medication report")
        html_data += medication_report(medication_data_array)

    # Add the sensors to the story if provided
    if sensor_data is not None and len(sensor_data) > 0:
        print("generating sensor report")
        html_data += sensor_report(sensor_data)
        # story.extend(sensor_story)

    return generate_pdf_to_byte_array(html_data)
