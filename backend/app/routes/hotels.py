"""
Endpoints de hoteles. Misma estrategia anti-quema que vuelos:
  - GET  /api/hotels/{dest}              → siempre lee Mongo (0 requests)
  - POST /api/hotels/import-json         → carga offline (0 requests)
  - POST /api/hotels/refresh             → ÚNICO punto que llama a RapidAPI (1 request)
  - GET  /api/hotels/{dest}/dates        → fechas disponibles en cache
  - GET  /api/hotels/{dest}/currency-audit → cuántos hoteles tuvieron el bug USD/MXN
"""
import httpx
from fastapi import APIRouter, Body, HTTPException, Query

from app.config import settings
from app.db import db, hotels_col, utcnow
from app.models.schemas import HotelsResponse
from app.services.hotels_normalizer import normalize_hotels

router = APIRouter(prefix="/api/hotels", tags=["hotels"])

# Booking dest_ids conocidos (para /refresh; opcional)
BOOKING_DEST_IDS = {
    "CUN": "-1655011",   # Cancún — confirmado en tu prueba original
    # Los demás se pueden agregar cuando se necesiten
}

# Endpoint RapidAPI Booking Hotels (ajusta si tu suscripción usa otro path)
HOTELS_ENDPOINT = "/api/v1/hotels/searchHotels"
usage_col = db["api_usage"]


async def _save_hotels(docs: list[dict]) -> int:
    """Upsert por (destination, checkin, checkout, hotelId)."""
    for doc in docs:
        await hotels_col.update_one(
            {
                "destination": doc["destination"],
                "checkinDate": doc["checkinDate"],
                "checkoutDate": doc["checkoutDate"],
                "hotelId": doc["hotelId"],
            },
            {"$set": doc},
            upsert=True,
        )
    return len(docs)


async def _log_api_call(params: dict) -> None:
    """Registra cada request real. Se suma al pool global de 20."""
    await usage_col.insert_one(
        {"endpoint": "hotels", "params": params, "timestamp": utcnow()}
    )


@router.get(
    "/{destination}/dates",
    summary="Fechas con hoteles cacheados para un destino",
)
async def available_dates(destination: str):
    pipeline = [
        {"$match": {"destination": destination.upper()}},
        {"$group": {
            "_id": {"checkin": "$checkinDate", "checkout": "$checkoutDate"},
            "count": {"$sum": 1},
            "minPrice": {"$min": "$price"},
        }},
        {"$sort": {"_id.checkin": 1}},
    ]
    rows = await hotels_col.aggregate(pipeline).to_list(length=100)
    return {
        "destination": destination.upper(),
        "dates": [
            {
                "checkin": r["_id"]["checkin"],
                "checkout": r["_id"]["checkout"],
                "count": r["count"],
                "minPrice": r["minPrice"],
            }
            for r in rows
        ],
    }


@router.get(
    "/{destination}/currency-audit",
    summary="Auditoría del bug USD/MXN: cuántos hoteles tuvieron moneda inconsistente",
)
async def currency_audit(destination: str):
    dest = destination.upper()
    total = await hotels_col.count_documents({"destination": dest})
    mismatches = await hotels_col.count_documents(
        {"destination": dest, "currencyMismatch": True}
    )
    examples = await hotels_col.find(
        {"destination": dest, "currencyMismatch": True},
        {"_id": 0, "name": 1, "declaredCurrency": 1, "currency": 1, "price": 1},
    ).limit(5).to_list(length=5)

    return {
        "destination": dest,
        "total_hotels": total,
        "hotels_with_currency_mismatch": mismatches,
        "mismatch_percentage": round((mismatches / total) * 100, 1) if total else 0,
        "examples": examples,
    }


@router.get(
    "/{destination}",
    response_model=HotelsResponse,
    summary="Hoteles cacheados (NO consume requests)",
)
async def get_hotels(
    destination: str,
    checkin: str = Query(..., description="YYYY-MM-DD"),
    checkout: str = Query(..., description="YYYY-MM-DD"),
    sort: str = Query("price", description="price | rating | stars"),
):
    dest = destination.upper()

    cursor = hotels_col.find(
        {"destination": dest, "checkinDate": checkin, "checkoutDate": checkout},
        {"_id": 0, "accessibilityLabel": 0, "fetchedAt": 0},
    )

    if sort == "rating":
        cursor = cursor.sort([("reviewScore", -1), ("price", 1)])
    elif sort == "stars":
        cursor = cursor.sort([("stars", -1), ("price", 1)])
    else:
        cursor = cursor.sort("price", 1)

    hotels = await cursor.to_list(length=500)

    if not hotels:
        raise HTTPException(
            404,
            f"Sin hoteles cacheados para {dest} ({checkin} → {checkout}). "
            f"Usa POST /api/hotels/import-json.",
        )

    mismatches = sum(1 for h in hotels if h.get("currencyMismatch"))
    return HotelsResponse(
        destination=dest,
        checkinDate=checkin,
        checkoutDate=checkout,
        source="cache",
        count=len(hotels),
        currencyMismatches=mismatches,
        hotels=hotels,
    )


@router.post(
    "/import-json",
    summary="Carga un JSON de Booking Hotels ya descargado (0 requests)",
)
async def import_hotels_json(
    destination: str = Query(...),
    checkin: str = Query(..., description="YYYY-MM-DD"),
    checkout: str = Query(..., description="YYYY-MM-DD"),
    adults: int = Query(2, ge=1, le=9),
    payload: dict = Body(..., description="JSON crudo de Booking Hotels"),
):
    docs, meta = normalize_hotels(
        payload, destination.upper(), checkin, checkout, adults
    )
    if not docs:
        raise HTTPException(400, "El JSON no contiene hoteles válidos")

    saved = await _save_hotels(docs)
    mismatches = sum(1 for d in docs if d.get("currencyMismatch"))
    meta_total_reported = None
    if isinstance(meta, dict):
        total = meta.get("totalCount")
        if isinstance(total, int):
            meta_total_reported = total
        elif isinstance(total, str) and total.isdecimal():
            meta_total_reported = int(total)
    elif isinstance(meta, list):
        for item in meta:
            title = item.get("title") if isinstance(item, dict) else None
            if isinstance(title, str):
                words = title.split(maxsplit=1)
                if words and words[0].isdecimal():
                    meta_total_reported = int(words[0])
                    break

    return {
        "saved": saved,
        "route_destination": destination.upper(),
        "checkin": checkin,
        "checkout": checkout,
        "currency_mismatches_detected": mismatches,
        "meta_total_reported": meta_total_reported,
        "note": "Cargado sin consumir requests de RapidAPI",
    }


@router.post(
    "/refresh",
    summary="CONSUME 1 REQUEST · Llama RapidAPI Booking Hotels",
)
async def refresh_hotels(
    destination: str = Query(...),
    checkin: str = Query(..., description="YYYY-MM-DD"),
    checkout: str = Query(..., description="YYYY-MM-DD"),
    adults: int = Query(2, ge=1, le=9),
    confirm: str = Query(..., description="Escribe 'yes'"),
    dest_id: str | None = Query(
        None,
        description="Booking dest_id. Si no se pasa, se busca en tabla interna.",
    ),
):
    if confirm.lower() != "yes":
        raise HTTPException(
            400, "Confirmación requerida. Agrega ?confirm=yes para consumir 1 request."
        )

    dest = destination.upper()

    # Resolver dest_id
    resolved_dest_id = dest_id or BOOKING_DEST_IDS.get(dest)
    if not resolved_dest_id:
        raise HTTPException(
            400,
            f"No tengo dest_id para {dest}. Pásalo como query param: "
            f"?dest_id=-XXXXXXX",
        )

    if not settings.rapidapi_key:
        raise HTTPException(500, "RAPIDAPI_KEY no configurada")

    # Cuota
    total_used = await usage_col.count_documents({"endpoint": {"$ne": "SEED"}})
    seed_doc = await usage_col.find_one({"endpoint": "SEED"})
    if seed_doc:
        total_used += seed_doc.get("used_before", 0)
    if total_used >= 20:
        raise HTTPException(
            429, f"Cuota agotada ({total_used}/20). No más llamadas a RapidAPI."
        )

    # Llamar API
    url = f"https://{settings.rapidapi_host}{HOTELS_ENDPOINT}"
    headers = {
        "X-RapidAPI-Key": settings.rapidapi_key,
        "X-RapidAPI-Host": settings.rapidapi_host,
    }
    params = {
        "dest_id": resolved_dest_id,
        "search_type": "city",
        "arrival_date": checkin,
        "departure_date": checkout,
        "adults": str(adults),
        "room_qty": "1",
        "page_number": "1",
        "units": "metric",
        "temperature_unit": "c",
        "languagecode": "es",
        "currency_code": "MXN",
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            raw = resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            502, f"Booking respondió {exc.response.status_code}: {exc.response.text[:300]}"
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Error de red: {exc}") from exc

    await _log_api_call(
        {
            "destination": dest,
            "checkin": checkin,
            "checkout": checkout,
            "adults": adults,
            "dest_id": resolved_dest_id,
        }
    )

    docs, _ = normalize_hotels(raw, dest, checkin, checkout, adults)
    if not docs:
        raise HTTPException(422, "Booking respondió sin hoteles válidos")

    saved = await _save_hotels(docs)
    mismatches = sum(1 for d in docs if d.get("currencyMismatch"))

    return {
        "saved": saved,
        "destination": dest,
        "checkin": checkin,
        "checkout": checkout,
        "currency_mismatches_detected": mismatches,
        "requests_used_total": total_used + 1,
        "requests_remaining": 20 - (total_used + 1),
    }