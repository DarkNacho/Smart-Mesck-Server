import asyncio
import websockets
from datetime import datetime
import random
from models import SensorData, SensorType


async def send_data(websocket, json_data):
    await websocket.send(json_data)


async def main():
    uri = "ws://localhost:8000/sensor2/arduino_ws?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkYXJrX25hY2hvX3hkQGhvdG1haWwuY2wiLCJpZCI6IjMiLCJuYW1lIjoiSWduYWNpbyBNYXJ0XHUwMGVkbmV6Iiwicm9sZSI6IlByYWN0aXRpb25lciIsImV4cCI6MTcxODY0NzI0Ni4wNzY2ODA0fQ.7vTiOHRUO-_h3T1-QnnK5ERant6iUXKuL-FTHRw6WPc"  # sin ssl
    # uri = "wss://castudillo-chart-server-sm.darknacho.xyz/sensor/arduino_ws_no_token"  # con ssl
    async with websockets.connect(uri) as websocket:
        for i in range(10):
            tasks = []
            for j in range(100):
                arduino_data = SensorData(
                    device=f"simulador-dummy",
                    sensor_type=SensorType.Temperatura,
                    timestamp_epoch=int(datetime.utcnow().timestamp()),
                    timestamp_millis=random.randint(0, 999),
                    value=random.uniform(30, 38),
                    patient_id="5",
                )
                json_data = arduino_data.model_dump_json()
                tasks.append(asyncio.create_task(send_data(websocket, json_data)))
            await asyncio.gather(*tasks)
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
