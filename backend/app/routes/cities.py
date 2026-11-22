"""Endpoints para consultar y sembrar el catálogo de ciudades."""
from fastapi import APIRouter, HTTPException

from app.db import cities_col

router = APIRouter(prefix="/api/cities", tags=["cities"])

# Fuente de verdad: 10 destinos mexicanos iniciales.
SEED_CITIES = [
    {"iata": "CUN", "name": "Cancún", "state": "Quintana Roo", "country": "MX",
     "lat": 21.1619, "lon": -86.8515, "timezone": "America/Cancun", "type": "playa"},
    {"iata": "MEX", "name": "Ciudad de México", "state": "CDMX", "country": "MX",
     "lat": 19.4326, "lon": -99.1332, "timezone": "America/Mexico_City", "type": "ciudad"},
    {"iata": "GDL", "name": "Guadalajara", "state": "Jalisco", "country": "MX",
     "lat": 20.6597, "lon": -103.3496, "timezone": "America/Mexico_City", "type": "ciudad"},
    {"iata": "PVR", "name": "Puerto Vallarta", "state": "Jalisco", "country": "MX",
     "lat": 20.6534, "lon": -105.2253, "timezone": "America/Mexico_City", "type": "playa"},
    {"iata": "SJD", "name": "Los Cabos", "state": "Baja California Sur", "country": "MX",
     "lat": 23.0588, "lon": -109.6970, "timezone": "America/Mazatlan", "type": "playa"},
    {"iata": "MID", "name": "Mérida", "state": "Yucatán", "country": "MX",
     "lat": 20.9674, "lon": -89.5926, "timezone": "America/Merida", "type": "ciudad"},
    {"iata": "HUX", "name": "Huatulco", "state": "Oaxaca", "country": "MX",
     "lat": 15.7749, "lon": -96.2627, "timezone": "America/Mexico_City", "type": "playa"},
    {"iata": "ZIH", "name": "Zihuatanejo", "state": "Guerrero", "country": "MX",
     "lat": 17.6417, "lon": -101.5514, "timezone": "America/Mexico_City", "type": "playa"},
    {"iata": "MTY", "name": "Monterrey", "state": "Nuevo León", "country": "MX",
     "lat": 25.6866, "lon": -100.3161, "timezone": "America/Monterrey", "type": "ciudad"},
    {"iata": "OAX", "name": "Oaxaca", "state": "Oaxaca", "country": "MX",
     "lat": 17.0732, "lon": -96.7266, "timezone": "America/Mexico_City", "type": "cultura"},
]


@router.get("", summary="Lista todas las ciudades del catálogo")
async def list_cities():
    """Lista las ciudades ordenadas alfabéticamente."""
    cursor = cities_col.find({}, {"_id": 0}).sort("name", 1)
    return await cursor.to_list(length=200)


@router.post("/seed", summary="Carga/actualiza las 10 ciudades iniciales")
async def seed_cities():
    """Idempotente: hace upsert de las 10 ciudades."""
    for city in SEED_CITIES:
        await cities_col.update_one(
            {"iata": city["iata"]},
            {"$set": city},
            upsert=True,
        )
    return {"inserted_or_updated": len(SEED_CITIES)}


@router.get("/{iata}", summary="Detalle de una ciudad")
async def get_city(iata: str):
    """Busca una ciudad por IATA o responde 404 si no existe."""
    doc = await cities_col.find_one({"iata": iata.upper()}, {"_id": 0})
    if not doc:
        raise HTTPException(404, f"Ciudad {iata} no encontrada")
    return doc