"""
POST /api/search — el endpoint estrella.

Combina clima histórico + vuelos cacheados + hoteles cacheados
y devuelve un ranking con scores.
"""
from fastapi import APIRouter, HTTPException
from app.services.booking_urls import build_flight_url, build_hotel_url

from app.db import cities_col, flights_col, hotels_col, weather_col
from app.models.schemas import (
    HotelSummary,
    FlightSummary,
    ScoredFlight,
    ScoredHotel,
    SearchRequest,
    SearchResponse,
    WeatherSummary,
)
from app.services.scoring import (
    MONTH_NAMES_ES,
    final_score,
    price_score,
    weather_score,
)

router = APIRouter(prefix="/api/search", tags=["search"])

# Reparto del presupuesto por defecto
FLIGHT_SHARE = 0.30
HOTEL_SHARE = 0.70


async def _get_month_climate(iata: str, month: str) -> dict | None:
    """Promedio mensual de clima cacheado para una ciudad."""
    pipeline = [
        {"$match": {"city": iata}},
        {"$addFields": {"month": {"$substr": ["$date", 5, 2]}}},
        {"$match": {"month": month}},
        {"$group": {
            "_id": None,
            "tempMaxC": {"$avg": "$tempMaxC"},
            "tempMinC": {"$avg": "$tempMinC"},
            "precipMm": {"$avg": "$precipitationMm"},
            "windKmh": {"$avg": "$windKmh"},
            "days": {"$sum": 1},
        }},
    ]
    rows = await weather_col.aggregate(pipeline).to_list(length=1)
    return rows[0] if rows else None


@router.post("/", response_model=SearchResponse, summary="Búsqueda unificada")
async def search(req: SearchRequest):
    origin = req.origin.upper()
    destination = req.destination.upper()
    warnings: list[str] = []

    # 1) Ciudad
    city = await cities_col.find_one({"iata": destination}, {"_id": 0})
    if not city:
        raise HTTPException(404, f"Ciudad {destination} no encontrada")

    # 2) Clima del mes de salida (histórico como proxy)
    month = req.departDate[5:7]
    month_name = MONTH_NAMES_ES[int(month) - 1]
    climate = await _get_month_climate(destination, month)

    ws: dict | None = None
    weather_summary: WeatherSummary | None = None
    if climate:
        ws = weather_score(
            climate["tempMaxC"], climate["tempMinC"],
            climate["precipMm"], climate["windKmh"],
            req.weatherPref,
        )
        weather_summary = WeatherSummary(
            month=month,
            monthName=month_name,
            tempMaxC=round(climate["tempMaxC"], 1),
            tempMinC=round(climate["tempMinC"], 1),
            precipMm=round(climate["precipMm"], 2),
            windKmh=round(climate["windKmh"], 1),
            daysAnalyzed=climate["days"],
            score=ws,
        )
    else:
        warnings.append(
            f"Sin clima cacheado para {destination}. Llama primero "
            f"/api/weather/{destination}. Score climático neutral (50)."
        )

    weather_sc = ws["total"] if ws else 50.0
    flight_budget = req.budget * FLIGHT_SHARE
    hotel_budget = req.budget * HOTEL_SHARE

    # 3) Vuelos cacheados
    raw_flights = await flights_col.find(
        {"origin": origin, "destination": destination, "departDate": req.departDate},
        {"_id": 0, "segments": 0, "token": 0, "fetchedAt": 0},
    ).to_list(length=200)

    flight_booking_url = build_flight_url(
        origin, destination, req.departDate, req.adults
    )
    for f in raw_flights:
        f["bookingUrl"] = flight_booking_url

    scored_flights: list[ScoredFlight] = []
    for f in raw_flights:
        try:
            fs = FlightSummary(**f)
        except Exception:
            continue
        ps = price_score(f["price"], flight_budget)
        fs_score = final_score(ps, weather_sc)
        scored_flights.append(ScoredFlight(
            flight=fs, priceScore=ps, weatherScore=weather_sc, finalScore=fs_score,
        ))
    scored_flights.sort(key=lambda x: -x.finalScore)

    if not raw_flights:
        warnings.append(
            f"Sin vuelos cacheados para {origin}→{destination} el {req.departDate}."
        )

    # 4) Hoteles cacheados
    # Default checkin = departDate, checkout = +3 noches
    checkin = req.checkin or req.departDate
    if req.checkout:
        checkout = req.checkout
    else:
        from datetime import date, timedelta
        checkout = (date.fromisoformat(checkin) + timedelta(days=3)).isoformat()

    raw_hotels = await hotels_col.find(
        {"destination": destination, "checkinDate": checkin, "checkoutDate": checkout},
        {"_id": 0, "accessibilityLabel": 0, "fetchedAt": 0},
    ).to_list(length=200)

    city_name = city["name"]  # ya lo tienes del bloque de arriba
    for h in raw_hotels:
        h["bookingUrl"] = build_hotel_url(
            city_name, h["checkinDate"], h["checkoutDate"], h.get("adults", 2)
        )

    scored_hotels: list[ScoredHotel] = []
    for h in raw_hotels:
        try:
            hs = HotelSummary(**h)
        except Exception:
            continue
        ps = price_score(h["price"], hotel_budget)
        hs_score = final_score(ps, weather_sc)
        scored_hotels.append(ScoredHotel(
            hotel=hs, priceScore=ps, weatherScore=weather_sc, finalScore=hs_score,
        ))
    scored_hotels.sort(key=lambda x: -x.finalScore)

    if not raw_hotels:
        warnings.append(
            f"Sin hoteles cacheados para {destination} ({checkin} → {checkout})."
        )

    # 5) Combinado
    best_f = scored_flights[0] if scored_flights else None
    best_h = scored_hotels[0] if scored_hotels else None
    trip_score: float | None = None
    if best_f and best_h:
        trip_score = round((best_f.finalScore + best_h.finalScore) / 2, 1)

    return SearchResponse(
        origin=origin,
        destination=destination,
        destName=city["name"],
        departDate=req.departDate,
        weatherPref=req.weatherPref,
        budget=req.budget,
        flightBudget=round(flight_budget, 2),
        hotelBudget=round(hotel_budget, 2),
        weather=weather_summary,
        topFlights=scored_flights[:3],
        topHotels=scored_hotels[:3],
        recommendedFlight=best_f,
        recommendedHotel=best_h,
        tripScore=trip_score,
        warnings=warnings,
    )