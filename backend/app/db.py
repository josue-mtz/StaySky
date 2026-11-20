"""Capa de acceso a MongoDB. Todo el proyecto importa desde aquí."""
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

client = AsyncIOMotorClient(settings.mongo_url)
db = client[settings.mongo_db]

# Colecciones tipadas (referencias reutilizables)
cities_col = db["cities"]
flights_col = db["flights"]
hotels_col = db["hotels"]
weather_col = db["weather"]
searches_col = db["searches"]


async def ensure_indexes() -> None:
    """
    Crea índices si no existen. Se llama al arrancar la app.
    Idempotente: si ya existen, no hace nada.
    """
    await cities_col.create_index("iata", unique=True)
    await weather_col.create_index([("city", 1), ("date", 1)], unique=True)
    await flights_col.create_index(
        [("origin", 1), ("destination", 1), ("departDate", 1)]
    )
    await hotels_col.create_index(
        [("destination", 1), ("checkinDate", 1), ("checkoutDate", 1)]
    )


def utcnow() -> datetime:
    """UTC naive, para guardar consistente en Mongo."""
    return datetime.now(timezone.utc).replace(tzinfo=None)