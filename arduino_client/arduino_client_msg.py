import asyncio
import websockets


async def receive_messages(uri):
    async with websockets.connect(uri) as websocket:
        await websocket.send("Hello, WebSocket server!")
        while True:
            message = await websocket.recv()
            print(f"Received message: {message}")

            # Process the message as needed


# Replace 'ws://your_websocket_server' with your actual WebSocket server URI
uri = "ws://alaya.cttn.cl:8088/sensor2/arduino_ws?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqYXZpZXIuc2lsdmFAdXRhbGNhLmNsIiwiaWQiOiIyNjIiLCJuYW1lIjoiSiAgUyBMIiwicm9sZSI6IlBhdGllbnQiLCJleHAiOjE3NDQ5NDU4NjUuODc1MDU5fQ.k99Pzmo9uo4voX79hT7KI75D1Niwdt8iSzegugfeE-s&encounter_id=110&rut=198625388"

# Start the event loop using the newer pattern
if __name__ == "__main__":
    asyncio.run(receive_messages(uri))
