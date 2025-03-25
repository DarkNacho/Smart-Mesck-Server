import asyncio
import websockets
from datetime import datetime
import random
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import SensorData, SensorType


async def send_data(websocket, json_data):
    await websocket.send(json_data)


async def main():
    # uri = "ws://localhost:8000/sensor2/arduino_ws?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJraXNpbmVnNTU2QGxvc3Z0bi5jb20iLCJpZCI6IjUiLCJyb2xlIjoiUGF0aWVudCIsIm5hbWUiOiJKdWFuIENhcmxvcyBCb2RvcXVlIiwiZXhwIjoxNzI0NDQ4NDEzLjQyNTIxMX0.m0wCVPlNdG6QJqQs2jN1Zj5nzY37vy1LK4bBoz5mxuc"  # sin ssl
    uri = "ws://alaya.cttn.cl:8088/sensor2/arduino_ws?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJraXNpbmVnNTU2QGxvc3Z0bi5jb20iLCJpZCI6IjUiLCJyb2xlIjoiQWRtaW4iLCJuYW1lIjoiSnVhbiBDYXJsb3MgQm9kb3F1ZSIsImV4cCI6MTczNDc4MDM2Ny4zODIzMjQ3fQ.3y8DM5csS7bUmEj4tsFBDj4cMvt1m1t79sanTUhGKaQ"  # con ssl
    # uri = "wss://castudillo-chart-server-sm.darknacho.software/sensor2/arduino_ws?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJraXNpbmVnNTU2QGxvc3Z0bi5jb20iLCJpZCI6IjUiLCJyb2xlIjoiUGF0aWVudCIsIm5hbWUiOiJKdWFuIENhcmxvcyBCb2RvcXVlIiwiZXhwIjoxNzI0NDQ4NDEzLjQyNTIxMX0.m0wCVPlNdG6QJqQs2jN1Zj5nzY37vy1LK4bBoz5mxuc"  # con ssl
    # uri = "wss://dn-server.darknacho.software/sensor2/arduino_ws?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJraXNpbmVnNTU2QGxvc3Z0bi5jb20iLCJpZCI6IjUiLCJyb2xlIjoiUGF0aWVudCIsIm5hbWUiOiJKdWFuIENhcmxvcyBCb2RvcXVlIiwiZXhwIjoxNzI0NDQ4NDEzLjQyNTIxMX0.m0wCVPlNdG6QJqQs2jN1Zj5nzY37vy1LK4bBoz5mxuc"  # con ssl"
    # uri = "wss://dn-server.darknacho.software/sensor/arduino_ws_no_token"
    async with websockets.connect(uri) as websocket:
        for i in range(100):
            tasks = []
            for j in range(1):
                arduino_data = SensorData(
                    device=f"simulador-dummy-das",
                    sensor_type=SensorType.Temperatura,
                    timestamp_epoch=int(datetime.utcnow().timestamp()),
                    timestamp_millis=random.randint(0, 999),
                    value=random.uniform(30, 38),
                    patient_id="7",
                    encounter_id="110",
                )
                json_data = arduino_data.model_dump_json()
                tasks.append(asyncio.create_task(send_data(websocket, json_data)))
            await asyncio.gather(*tasks)
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
