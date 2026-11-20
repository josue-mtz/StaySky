from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.routes.cities import router as cities_router
from app.routes.weather import router as weather_router

app = FastAPI(
    title="StaySky - Buscador de Viajes por Clima + Presupuesto",
    version="0.1.0",
)

# Cliente Mongo (conexión lazy: se abre al primer uso)
client = AsyncIOMotorClient(settings.mongo_url)
db = client[settings.mongo_db]
app.include_router(cities_router)
app.include_router(weather_router)

# Sirve archivos estáticos (CSS, JS, imágenes) desde /static
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/health", tags=["infra"])
async def health():
    """Ping a MongoDB. Devuelve estado real de la conexión."""
    try:
        await client.admin.command("ping")
        mongo_status = "connected"
    except Exception:
        mongo_status = "down"
    return {"status": "ok", "mongo": mongo_status}


@app.get("/", include_in_schema=False)
async def root():
    """Sirve el index.html del frontend."""
    return FileResponse("frontend/index.html")