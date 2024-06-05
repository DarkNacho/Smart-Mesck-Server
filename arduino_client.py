import asyncio
import websockets
from datetime import datetime
import random
from models import SensorData, SensorType


async def send_data(websocket, json_data):
    await websocket.send(json_data)


async def main():
    uri = "ws://localhost:8000/sensor/arduino_ws_no_token"  # sin ssl
    # uri = "wss://castudillo-chart-server-sm.darknacho.xyz/sensor/arduino_ws_no_token"  # con ssl
    async with websockets.connect(uri) as websocket:
        for i in range(10):
            tasks = []
            for j in range(100):
                arduino_data = SensorData(
                    device=f"simulador-dummy",
                    sensor_type=SensorType.Temperatura,
                    timestamp_epoch=int(datetime.now().timestamp()),
                    timestamp_millis=random.randint(0, 999),
                    value=random.uniform(30, 38),
                )
                json_data = arduino_data.model_dump_json()
                tasks.append(asyncio.create_task(send_data(websocket, json_data)))
            await asyncio.gather(*tasks)
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
