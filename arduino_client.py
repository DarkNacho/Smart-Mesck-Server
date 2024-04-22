import asyncio
import websockets
from datetime import datetime
import json
import random


async def send_data():
    uri = "ws://localhost:8000/sensor/arduino_ws"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJuYWNob0BuYWNoby5jbCIsImlkIjoxLCJleHAiOjE3MTM1NDA5ODUuNjQ3OTk2Mn0.k7QTjJhcM9wn9xXr3WwYAUSx8zmrv8-E7JonY0Pai_o"
    #token = "Bearer dsad"
    async with websockets.connect(uri + f"?token={token}") as websocket:
        while True:
            arduino_data = {
                "device": "simulador-1",
                "sensor": "temperatura",
                "time": datetime.now().isoformat(),
                "value": random.uniform(30, 38)
            }
            json_data = json.dumps(arduino_data)
            await websocket.send(json_data)
            
            arduino_data = {
                "device": "simulador-2",
                "sensor": "co2",
                "time": datetime.now().isoformat(),
                "value": random.uniform(300, 500)
            }
            json_data = json.dumps(arduino_data)
            await websocket.send(json_data)
            
            arduino_data = {
                "device": "simulador-1",
                "sensor": "co2",
                "time": datetime.now().isoformat(),
                "value": random.uniform(300, 500)
            }
            json_data = json.dumps(arduino_data)
            await websocket.send(json_data)

            
            print(f"sending data...")
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(send_data())
