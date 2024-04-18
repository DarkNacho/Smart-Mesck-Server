from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
import uvicorn
import asyncio
import json

from database import get_session
from models import User


from auth import router as auth_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Puedes ajustar esto según tus necesidades de seguridad
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

arduino_clients = set()
dashboard_clients = set()

@app.websocket("/arduino_ws")
async def arduino_websocket(websocket: WebSocket):
    await websocket.accept()
    arduino_clients.add(websocket)
    print(f"Arduino connected: {websocket.client.host}")

    try:
        while True:
            data = await websocket.receive_text()
            try:
                json_data = json.loads(data)
                # Process Arduino JSON data as needed
                print(f"Received JSON data from Arduino: {json_data}")
                # Broadcast JSON data to all dashboard clients
                for dashboard_client in dashboard_clients:
                    await dashboard_client.send_json(json_data)
            except json.JSONDecodeError:
                print(f"Invalid JSON data received from Arduino: {data}")
    except asyncio.CancelledError:
        pass
    except WebSocketDisconnect:
        pass
    finally:
        arduino_clients.remove(websocket)
        print(f"Arduino disconnected: {websocket.client.host}")

@app.websocket("/dashboard_ws")
async def dashboard_websocket(websocket: WebSocket):
    await websocket.accept()
    dashboard_clients.add(websocket)
    print(f"Dashboard connected: {websocket.client.host}")

    try:
        while True:
            # Dashboard clients can listen for JSON data sent by Arduino devices
            data = await websocket.receive_json()
            print(f"Received JSON data in dashboard: {data}")
    except asyncio.CancelledError:
        pass
    except WebSocketDisconnect:
        pass
    finally:
        dashboard_clients.remove(websocket)
        print(f"Dashboard disconnected: {websocket.client.host}")


@app.post("/register_user")
async def send_data(data: User, db: Session = Depends(get_session)):
    print(data)
    db.add(data)
    db.commit()
    
    
if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
