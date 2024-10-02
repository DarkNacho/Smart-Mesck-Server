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
uri = "wss://dn-server.darknacho.software/sensor2/arduino_ws?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJraXNpbmVnNTU2QGxvc3Z0bi5jb20iLCJpZCI6IjUiLCJyb2xlIjoiUGF0aWVudCIsIm5hbWUiOiJKdWFuIENhcmxvcyBCb2RvcXVlIiwiZXhwIjoxNzI0NDQ4NDEzLjQyNTIxMX0.m0wCVPlNdG6QJqQs2jN1Zj5nzY37vy1LK4bBoz5mxuc"  # con ssl

# Start the event loop
asyncio.get_event_loop().run_until_complete(receive_messages(uri))
