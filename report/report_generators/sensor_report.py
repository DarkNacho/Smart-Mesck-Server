import io
from collections import defaultdict
import matplotlib.pyplot as plt


from report.report_utils import render_template
from dateutil.parser import isoparse
import os
import base64


def sensor_report(data):

    context_title = {
        "title": "Reporte Sensores",
        "img_path": os.path.abspath("report/static/icon_sensores.png"),
    }

    html = render_template("template_title.html", context_title)
    # html = ""
    sensorData = defaultdict(lambda: defaultdict(list))

    for encounter_id, encounter_data in data.items():

        header_table = [
            "Sensor Type",
            "Min",
            "Max",
            "Avg",
            "Count",
            # "Day",
            "Start",
            "End",
            "Duration",
        ]

        for sensor_type, sensor_data in encounter_data.items():
            sensorData[sensor_type]["min"].append(sensor_data["min"])
            sensorData[sensor_type]["max"].append(sensor_data["max"])
            sensorData[sensor_type]["avg"].append(sensor_data["avg"])
            sensorData[sensor_type]["timestamp_epoch"].append(sensor_data["start"])
            sensorData[sensor_type]["timestamps"].extend(sensor_data["timestamps"])
            sensorData[sensor_type]["values"].extend(sensor_data["values"])

            row = [{"value": sensor_type}]
            row.extend(
                [
                    {"value": sensor_data["min"]},
                    {"value": sensor_data["max"]},
                    {"value": sensor_data["avg"]},
                    {"value": sensor_data["count"]},
                    # {"value": sensor_data["day"]},
                    {"value": sensor_data["start"]},
                    {"value": sensor_data["end"]},
                    {"value": sensor_data["duration"]},
                ]
            )
        # quizás obtener el encuentro usando encounter_id y dar una info de por ejemplo que Profesional atendió
        context = {
            "title": f"{sensor_data['day']} - Encuentro {encounter_id}",
            "table_data": row,
            "header_list": header_table,
        }
        html += render_template("template_sensor.html", context)

    context_title = {
        "title": "Gráficas Reporte Sensores",
        "img_path": os.path.abspath("report/static/icon_sensores.png"),
    }

    html += render_template("template_title.html", context_title)

    for sensor_type, stats in sensorData.items():
        ## Graph de todos los valores
        plt.figure()
        plt.plot(stats["timestamps"], stats["values"])
        plt.xlabel("Hora")
        plt.ylabel("Valor")
        plt.legend()
        plt.tight_layout()

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png")
        plt.close()
        img_buffer.seek(0)
        img_data = base64.b64encode(img_buffer.getvalue()).decode("utf-8")

        context_graph = {
            "title": f"{sensor_type} en el tiempo",
            "img_path": os.path.abspath("report/static/icon_graph.png"),
            "img_data": img_data,
        }
        html += render_template("template_graph.html", context_graph)

        if len(data) == 1:
            continue

        ## Summary Graph

        plt.figure()
        plt.plot(stats["timestamp_epoch"], stats["min"], label="Min", marker="o")
        plt.plot(stats["timestamp_epoch"], stats["max"], label="Max", marker="o")
        plt.plot(stats["timestamp_epoch"], stats["avg"], label="Avg", marker="o")
        # plt.title(f"{sensor_type} Sensor Data")
        plt.xlabel("Día")
        plt.ylabel("Valor")
        plt.legend()
        plt.tight_layout()

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png")
        plt.close()
        img_buffer.seek(0)
        img_data = base64.b64encode(img_buffer.getvalue()).decode("utf-8")

        context_graph = {
            "title": f"{sensor_type} Estadísticas",
            "img_path": os.path.abspath("report/static/icon_graph.png"),
            "img_data": img_data,
        }
        html += render_template("template_graph.html", context_graph)
        # html += f'<img src="data:image/png;base64,{img_data}"/>'

    return html
