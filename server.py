from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn

# qr
import qrcode
from io import BytesIO

# routes
from sensor import router as sensor_router
from sensor3 import router as sensor2_router
from auth import router as auth_router, isAuthorized
from file_manager import router as file_router
from report2 import router as reporte_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Puedes ajustar esto según tus necesidades de seguridad
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],  # Exponer el encabezado Content-Disposition
)

app.include_router(auth_router)
app.include_router(sensor_router)
app.include_router(sensor2_router)
app.include_router(file_router)
app.include_router(reporte_router)


@app.get("/test_token")
async def test(payload=Depends(isAuthorized)):
    return {"payload": payload}


@app.get("/javier")
async def javier():
    return {"mensaje": "Hola Javier"}


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
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
