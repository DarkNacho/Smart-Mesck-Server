from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn

# qr
import qrcode
from io import BytesIO

# routes
from sensor import router as sensor_router
from sensor2 import router as sensor2_router
from auth import router as auth_router, isAuthorized
from file_manager import router as file_router
from report.routes import router as reporte_router
from gameData import router as gameData_router

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get allowed origins from .env and split them into a list
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Dynamically load allowed origins
    allow_credentials=True,  # Only if credentials are required
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Restrict to necessary methods
    allow_headers=["Authorization", "Content-Type"],  # Restrict to necessary headers
    expose_headers=["Content-Disposition"],  # Keep if needed for file downloads
)

app.include_router(auth_router)
app.include_router(sensor_router)
app.include_router(sensor2_router)
app.include_router(file_router)
app.include_router(reporte_router)
app.include_router(gameData_router)


@app.get("/test_token")
async def test(payload=Depends(isAuthorized)):
    return {"payload": payload}


@app.get("/generate_qr")
async def generate_qr(data: str):
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=15,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Create an image from the QR Code instance
    img = qr.make_image(fill="black", back_color="white")

    # Save the image to a BytesIO object
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    return StreamingResponse(img_byte_arr, media_type="image/png")


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8088, reload=True)
