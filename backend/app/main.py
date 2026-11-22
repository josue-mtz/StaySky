"""Punto de entrada de FastAPI: ciclo de vida, rutas y archivos estáticos."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.db import ensure_indexes
from app.routes import admin, cities, flights, hotels, search, weather

client = AsyncIOMotorClient(settings.mongo_url)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepara índices al iniciar y cierra la conexión con Mongo al terminar."""
    await ensure_indexes()
    yield
    client.close()


app = FastAPI(
    title="StaySky · Buscador de Viajes por Clima + Presupuesto",
    version="0.3.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.include_router(cities.router)
app.include_router(weather.router)
app.include_router(flights.router)
app.include_router(hotels.router)
app.include_router(search.router)
app.include_router(admin.router)

@app.get("/health", tags=["infra"])
async def health():
    """Devuelve el estado de la API y comprueba la conexión con MongoDB."""
    try:
        await client.admin.command("ping")
        mongo_status = "connected"
    except Exception:
        mongo_status = "down"
    return {"status": "ok", "mongo": mongo_status}


@app.get("/", include_in_schema=False)
async def root():
    """Sirve la página principal de StaySky."""
    return FileResponse("frontend/index.html")
