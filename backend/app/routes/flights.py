"""
Endpoints de vuelos.

REGLA CRÍTICA DE DISEÑO:
  - GET /api/flights/{origin}/{destination}  → SIEMPRE lee de Mongo (0 requests)
  - POST /api/flights/refresh                → ÚNICO punto que llama a RapidAPI
  - POST /api/flights/import-json            → Carga JSON offline (0 requests)
  - GET  /api/flights/usage                  → Monitorea uso de la cuota
"""
from fastapi import APIRouter, Body, HTTPException, Query

from app.db import db, flights_col, utcnow
from app.models.schemas import FlightsResponse
from app.services.booking_client import BookingApiError, search_flights
from app.services.flights_normalizer import normalize_offers
from app.services.booking_urls import build_flight_url

router = APIRouter(prefix="/api/flights", tags=["flights"])

MONTHLY_LIMIT = 20  # Plan Basic RapidAPI
usage_col = db["api_usage"]
aggregations_col = db["flight_aggregations"]


async def _save_offers(
    docs: list[dict], aggregation: dict | None, origin: str, destination: str, date: str
) -> int:
    """Guarda ofertas + aggregation en Mongo. Upsert para evitar duplicados."""
    for doc in docs:
        await flights_col.update_one(
            {
                "origin": doc["origin"],
                "destination": doc["destination"],
                "departDate": doc["departDate"],
                "flightKey": doc["flightKey"],
            },
            {"$set": doc},
            upsert=True,
        )
    if aggregation:
        await aggregations_col.update_one(
            {"origin": origin, "destination": destination, "departDate": date},
            {"$set": {"aggregation": aggregation, "fetchedAt": utcnow()}},
            upsert=True,
        )
    return len(docs)


async def _log_api_call(params: dict) -> None:
    await usage_col.insert_one({"endpoint": "flights", "params": params, "timestamp": utcnow()})


@router.get(
    "/usage",
    summary="Cuántos requests de RapidAPI has gastado",
)
async def usage():
    logged = await usage_col.count_documents({"endpoint": {"$ne": "SEED"}})
    seed_doc = await usage_col.find_one({"endpoint": "SEED"})
    seeded = seed_doc.get("used_before", 0) if seed_doc else 0
    total = logged + seeded
    return {
        "used": total,
        "logged_by_system": logged,
        "pre_existing": seeded,
        "limit": MONTHLY_LIMIT,
        "remaining": max(0, MONTHLY_LIMIT - total),
        "warning": (
            "MENOS DE 5 REQUESTS. Evita llamadas reales."
            if (MONTHLY_LIMIT - total) < 5
            else None
        ),
    }


@router.post(
    "/usage/seed",
    summary="Registra llamadas ya hechas antes de usar este sistema",
)
async def seed_usage(used_before: int = Query(..., ge=0)):
    await usage_col.delete_many({"endpoint": "SEED"})
    await usage_col.insert_one(
        {"endpoint": "SEED", "used_before": used_before, "timestamp": utcnow()}
    )
    return {"seeded": used_before}


@router.get(
    "/{origin}/{destination}",
    response_model=FlightsResponse,
    summary="Vuelos cacheados (NO consume requests)",
)
async def get_flights(
    origin: str,
    destination: str,
    date: str = Query(..., description="YYYY-MM-DD"),
    adults: int = Query(1, ge=1, le=9),
):
    origin, destination = origin.upper(), destination.upper()

    cursor = flights_col.find(
        {"origin": origin, "destination": destination, "departDate": date},
        {"_id": 0, "segments": 0, "token": 0, "fetchedAt": 0},
    ).sort("price", 1)
    flights = await cursor.to_list(length=500)

    if not flights:
        raise HTTPException(
            404,
            f"Sin vuelos cacheados para {origin}→{destination} el {date}. "
            f"Usa POST /api/flights/import-json o (con mucho cuidado) /refresh.",
        )

    booking_url = build_flight_url(origin, destination, date, adults)
    for f in flights:
        f["bookingUrl"] = booking_url

    agg_doc = await aggregations_col.find_one(
        {"origin": origin, "destination": destination, "departDate": date},
        {"_id": 0},
    )

    return FlightsResponse(
        origin=origin,
        destination=destination,
        departDate=date,
        source="cache",
        count=len(flights),
        aggregation=(agg_doc or {}).get("aggregation"),
        flights=flights,
    )


@router.get(
    "/{origin}/{destination}/dates",
    summary="Qué fechas tienen datos cacheados para esta ruta",
)
async def available_dates(origin: str, destination: str):
    pipeline = [
        {"$match": {"origin": origin.upper(), "destination": destination.upper()}},
        {"$group": {"_id": "$departDate", "count": {"$sum": 1},
                    "minPrice": {"$min": "$price"}}},
        {"$sort": {"_id": 1}},
    ]
    rows = await flights_col.aggregate(pipeline).to_list(length=100)
    return {
        "origin": origin.upper(),
        "destination": destination.upper(),
        "dates": [
            {"date": r["_id"], "count": r["count"], "minPrice": r["minPrice"]}
            for r in rows
        ],
    }


@router.post(
    "/import-json",
    summary="Carga un JSON de Booking ya descargado (0 requests)",
)
async def import_flights_json(
    origin: str = Query(...),
    destination: str = Query(...),
    date: str = Query(..., description="YYYY-MM-DD"),
    payload: dict = Body(..., description="JSON crudo de Booking (respuesta completa)"),
):
    """No llama a RapidAPI. Solo procesa y guarda lo que ya tienes."""
    docs, aggregation = normalize_offers(payload, origin.upper(), destination.upper(), date)
    if not docs:
        raise HTTPException(400, "El JSON no contiene flightOffers válidos")

    saved = await _save_offers(docs, aggregation, origin.upper(), destination.upper(), date)
    return {
        "saved": saved,
        "aggregation_present": aggregation is not None,
        "route": f"{origin.upper()}→{destination.upper()}",
        "date": date,
    }


@router.post(
    "/refresh",
    summary="CONSUME 1 REQUEST · Llama RapidAPI y guarda",
)
async def refresh_flights(
    origin: str = Query(...),
    destination: str = Query(...),
    date: str = Query(..., description="YYYY-MM-DD"),
    confirm: str = Query(..., description="Escribe 'yes' para confirmar"),
    adults: int = Query(1, ge=1, le=9),
):
    """
    Cada llamada = 1 request de tu cuota mensual.
    Requiere confirm=yes para evitar llamadas accidentales.
    """
    if confirm.lower() != "yes":
        raise HTTPException(
            400,
            "Confirmación requerida. Agrega ?confirm=yes para consumir 1 request.",
        )

    usage_now = await usage()
    if usage_now["remaining"] <= 0:
        raise HTTPException(
            429,
            f"Cuota agotada ({usage_now['used']}/{usage_now['limit']}). No más llamadas.",
        )

    try:
        raw = await search_flights(origin, destination, date, adults)
    except BookingApiError as exc:
        raise HTTPException(502, str(exc)) from exc

    await _log_api_call({
        "origin": origin.upper(),
        "destination": destination.upper(),
        "date": date,
        "adults": adults,
    })

    docs, aggregation = normalize_offers(raw, origin.upper(), destination.upper(), date)
    if not docs:
        raise HTTPException(
            422, "Booking respondió sin ofertas válidas. Revisa fechas/parámetros."
        )

    saved = await _save_offers(docs, aggregation, origin.upper(), destination.upper(), date)
    return {
        "saved": saved,
        "route": f"{origin.upper()}→{destination.upper()}",
        "date": date,
        "requests_used_total": usage_now["used"] + 1,
        "requests_remaining": usage_now["remaining"] - 1,
    }