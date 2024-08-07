from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# routes
from sensor import router as sensor_router
from sensor2 import router as sensor2_router
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
)

app.include_router(auth_router)
app.include_router(sensor_router)
app.include_router(sensor2_router)
app.include_router(file_router)
app.include_router(reporte_router)


@app.get("/test_token")
async def test(payload=Depends(isAuthorized)):
    return {"payload": payload}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
