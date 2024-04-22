
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, WebSocketException,status
import json

from jose import JWTError


from auth import decode_token

router = APIRouter(prefix="/sensor", tags=["sensor"])

arduino_clients = set()
dashboard_clients = set()


@router.websocket("/arduino_ws")
async def arduino_websocket(websocket: WebSocket, token : str):
    try:
        payload = await decode_token(token)
        print("payload:", payload)
        print("token:", token)
    except JWTError:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        
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
        
        
        
        
@router.websocket("/dashboard_ws")
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

