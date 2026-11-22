"""Endpoint de clima histórico con caché en MongoDB."""
from fastapi import APIRouter, HTTPException, Query

from app.db import cities_col, weather_col, utcnow
from app.models.schemas import WeatherResponse
from app.services.weather_client import fetch_open_meteo

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get(
    "/{iata}",
    response_model=WeatherResponse,
    summary="Clima histórico diario de una ciudad",
)
async def get_weather(
    iata: str,
    start_date: str = Query("2023-01-01", description="YYYY-MM-DD"),
    end_date: str = Query("2023-12-31", description="YYYY-MM-DD"),
    refresh: bool = Query(False, description="Fuerza llamada a la API"),
):
    """Devuelve clima diario desde caché o consulta Open-Meteo si hace falta."""
    iata = iata.upper()

    # 1) Validar ciudad
    city = await cities_col.find_one({"iata": iata})
    if not city:
        raise HTTPException(404, f"Ciudad {iata} no encontrada. Corre /api/cities/seed")

    # 2) ¿Hay caché suficiente? (>= 90% de días cubiertos)
    if not refresh:
        cached = await weather_col.find(
            {"city": iata, "date": {"$gte": start_date, "$lte": end_date}},
            {"_id": 0},
        ).to_list(length=1000)

        if cached:
            from datetime import date
            expected = (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days + 1
            if len(cached) >= expected * 0.9:
                return WeatherResponse(
                    city=iata, source="cache", count=len(cached), data=cached
                )

    # 3) Llamar a Open-Meteo
    try:
        rows = await fetch_open_meteo(city["lat"], city["lon"], start_date, end_date)
    except Exception as exc:
        raise HTTPException(502, f"Error consultando Open-Meteo: {exc}") from exc

    # 4) Upsert a Mongo (idempotente: re-ejecutar no duplica)
    for row in rows:
        await weather_col.update_one(
            {"city": iata, "date": row["date"]},
            {"$set": {**row, "city": iata, "fetchedAt": utcnow()}},
            upsert=True,
        )

    clean = [{**r, "city": iata} for r in rows]
    return WeatherResponse(city=iata, source="api", count=len(clean), data=clean)


@router.get(
    "/{iata}/climate",
    summary="Promedios mensuales (clima típico) de una ciudad",
)
async def get_climate(iata: str):
    """
    Agrega el histórico cacheado por mes calendario (01..12).
    Sirve para comparar 'cómo es marzo en Cancún' vs 'marzo en Los Cabos'.
    """
    iata = iata.upper()
    pipeline = [
        {"$match": {"city": iata}},
        {"$group": {
            "_id": {"$substr": ["$date", 5, 2]},  # mes "01".."12"
            "tempMaxC":  {"$avg": "$tempMaxC"},
            "tempMinC":  {"$avg": "$tempMinC"},
            "precipMm":  {"$avg": "$precipitationMm"},
            "windKmh":   {"$avg": "$windKmh"},
            "days":      {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    rows = await weather_col.aggregate(pipeline).to_list(length=12)
    if not rows:
        raise HTTPException(
            404,
            f"Sin clima cacheado para {iata}. Llama primero /api/weather/{iata}",
        )
    return {
        "city": iata,
        "months": [
            {
                "month": r["_id"],
                "tempMaxC": round(r["tempMaxC"], 1),
                "tempMinC": round(r["tempMinC"], 1),
                "precipMm": round(r["precipMm"], 2),
                "windKmh": round(r["windKmh"], 1),
                "days": r["days"],
            }
            for r in rows
        ],
    }