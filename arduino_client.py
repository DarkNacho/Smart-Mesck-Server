import asyncio
import websockets
from datetime import datetime
import json
import random


async def send_data(websocket, json_data):
    await websocket.send(json_data)


async def main():
    # uri = "ws://localhost:8000/sensor/arduino_ws?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJleGFtcGxlQGV4YW1wbGUuY29tIiwiaWQiOiIxIiwicm9sZSI6IkFkbWluIiwiZXhwIjoxNzE2MjE0MTk1LjA5NDg0Mn0.hr286g0Cg75PaubxMLhStuaakaATnVtokoJ3uiNP7HQ"
    uri = "ws://localhost:8000/sensor/arduino_ws_no_token"

    async with websockets.connect(uri) as websocket:
        while True:
            tasks = []
            for i in range(1):
                for j in range(8):
                    arduino_data = {
                        "device": f"simulador-{i}",
                        "sensor": f"sensor-{j}",
                        "time": datetime.now().isoformat(),
                        "value": random.uniform(30, 38),
                    }
                    json_data = json.dumps(arduino_data)
                    tasks.append(asyncio.create_task(send_data(websocket, json_data)))
            await asyncio.gather(*tasks)
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
