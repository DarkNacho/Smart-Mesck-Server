import asyncio
import websockets
from datetime import datetime, UTC
import random
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import SensorData, SensorType


async def send_without_response(websocket, json_data):
    """Solo envía datos sin esperar respuesta."""
    await websocket.send(json_data)
    print(f"Sent data: {json_data[:50]}...")


async def main():
    uri = "ws://alaya.cttn.cl:8088/sensor2/arduino_ws?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkYXJrX25hY2hvX3hkQGhvdG1haWwuY2wiLCJpZCI6IjEiLCJuYW1lIjoiSWduYWNpbyBNYXJ0XHUwMGVkbmV6Iiwicm9sZSI6IkFkbWluIiwiZXhwIjoxNzQ0OTI1ODA0LjIyODcwNjZ9.Q1XkP4Ule8roRQec3sapEyTtIs-1Hez1ZYvFI64S0oE"

    print("Connecting to server...")
    async with websockets.connect(uri) as websocket:
        # Recibir el primer mensaje de greeting del servidor
        greeting = await websocket.recv()
        print(f"Server greeting: {greeting}")

        # Extraer encounter_id del mensaje si está disponible
        encounter_id = "110"  # Valor predeterminado
        if greeting.startswith("encounter_id:"):
            encounter_id = greeting.split(":")[1].strip()
            print(f"Using encounter_id: {encounter_id}")

        # Crear tarea para manejar mensajes entrantes del servidor
        async def handle_server_messages():
            while True:
                try:
                    message = await websocket.recv()
                    print(f"Server message: {message}")
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed")
                    break
                except Exception as e:
                    print(f"Error receiving message: {e}")
                    break

        # Inicia la tarea para manejar mensajes del servidor en segundo plano
        server_task = asyncio.create_task(handle_server_messages())

        # Bucle principal para enviar datos
        try:
            for i in range(100):
                # Crear timestamp común para este conjunto de lecturas
                current_time = datetime.now(UTC)
                timestamp_epoch = int(current_time.timestamp())
                timestamp_millis = random.randint(0, 999)
                patient_id = "7"  # ID del paciente

                # Crear datos para cada sensor
                # 1. SpO2
                spo2_data = SensorData(
                    device="Pulsioxímetro",
                    sensor_type="SpO2",
                    timestamp_epoch=timestamp_epoch,
                    timestamp_millis=timestamp_millis,
                    value=random.uniform(95, 99),  # Valores normales de SpO2
                    patient_id=patient_id,
                    encounter_id=encounter_id,
                )

                # 2. Frecuencia Cardíaca
                heart_rate_data = SensorData(
                    device="Monitor Cardíaco",
                    sensor_type="Frecuencia Cardíaca",
                    timestamp_epoch=timestamp_epoch,
                    timestamp_millis=timestamp_millis,
                    value=random.randint(
                        60, 100
                    ),  # Valores normales de frecuencia cardíaca
                    patient_id=patient_id,
                    encounter_id=encounter_id,
                )

                # 3. Frecuencia Respiratoria
                resp_rate_data = SensorData(
                    device="Monitor Respiratorio",
                    sensor_type="Frecuencia Respiratoria",
                    timestamp_epoch=timestamp_epoch,
                    timestamp_millis=timestamp_millis,
                    value=random.randint(
                        12, 20
                    ),  # Valores normales de frecuencia respiratoria
                    patient_id=patient_id,
                    encounter_id=encounter_id,
                )

                # Convertir a JSON
                spo2_json = spo2_data.model_dump_json()
                heart_rate_json = heart_rate_data.model_dump_json()
                resp_rate_json = resp_rate_data.model_dump_json()

                # Enviar datos secuencialmente
                await send_without_response(websocket, spo2_json)
                await asyncio.sleep(0.1)  # Pequeña pausa entre envíos
                await send_without_response(websocket, heart_rate_json)
                await asyncio.sleep(0.1)  # Pequeña pausa entre envíos
                await send_without_response(websocket, resp_rate_json)

                print(f"Ciclo {i+1}/100: Datos enviados para los 3 sensores")

                # Esperar antes del siguiente conjunto de lecturas
                await asyncio.sleep(1)

        finally:
            # Cancelar la tarea de recepción de mensajes cuando termine el bucle principal
            server_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Programa detenido por el usuario")
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
