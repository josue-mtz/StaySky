"""
Transforma el JSON crudo de Booking en documentos planos para MongoDB.
Diseñado para ser determinista: mismo input → mismo output.
"""
from typing import Any

from app.db import utcnow


def money_to_float(money: dict | None) -> float | None:
    """
    Convierte {currencyCode, units, nanos} a float.
    Ej: {units: 1342, nanos: 0} → 1342.0
        {units: 1812, nanos: 650000000} → 1812.65
    """
    if not money:
        return None
    units = money.get("units", 0)
    nanos = money.get("nanos", 0)
    return round(units + nanos * 1e-9, 2)


def extract_offers(payload: dict) -> tuple[list[dict], dict | None]:
    """
    Acepta tanto la respuesta completa de RapidAPI como el payload 'data' solo.
    Devuelve (lista de flightOffers, aggregation).
    """
    data = payload.get("data", payload)
    offers = data.get("flightOffers") or data.get("offers") or []
    aggregation = data.get("aggregation")
    return offers, aggregation


def _get_airline_from_leg(leg: dict) -> dict:
    """Extrae {code, name} del primer carrier disponible en un leg."""
    carriers_data = leg.get("carriersData") or []
    if carriers_data:
        c = carriers_data[0]
        return {"code": c.get("code", ""), "name": c.get("name", "")}
    return {"code": "", "name": ""}


def _get_flight_number(leg: dict, airline_code: str) -> str:
    """Combina código de aerolínea + número del vuelo. Ej: VB1380."""
    fi = leg.get("flightInfo") or {}
    num = fi.get("flightNumber")
    if num is None:
        return ""
    return f"{airline_code}{num}"


def normalize_offer(
    offer: dict,
    origin: str,
    destination: str,
    depart_date: str,
) -> dict | None:
    """
    Normaliza UNA oferta. Devuelve None si le faltan datos esenciales.
    """
    segments = offer.get("segments") or []
    if not segments:
        return None
    seg = segments[0]
    legs = seg.get("legs") or []
    if not legs:
        return None

    # Aerolínea + número de vuelo (del primer leg)
    first_leg = legs[0]
    airline = _get_airline_from_leg(first_leg)
    flight_number = _get_flight_number(first_leg, airline["code"])

    # Escalas: legs - 1 (si hay 1 leg = directo, 2 legs = 1 escala)
    stops = max(0, len(legs) - 1)

    # Duración: totalTime viene en SEGUNDOS
    duration_min = int((seg.get("totalTime") or 0) / 60)

    # Precios
    pb = offer.get("priceBreakdown") or {}
    price = money_to_float(pb.get("total"))
    price_rounded = money_to_float(pb.get("totalRounded"))
    price_before = money_to_float(pb.get("totalWithoutDiscount"))

    if price is None:
        return None

    # Moneda (viene dentro de priceBreakdown.total)
    currency = (pb.get("total") or {}).get("currencyCode", "MXN")

    # Badges tipo ["CHEAPEST", "BEST", "FASTEST"]
    badges = [b.get("type") for b in (offer.get("badges") or []) if b.get("type")]

    # Equipaje incluido
    included = offer.get("includedProducts") or {}
    seg_included = (included.get("segments") or [[]])[0]
    luggage_types = [item.get("luggageType") for item in seg_included]
    has_checked_included = "CHECKED_IN" in luggage_types

    # Productos extra (precios opcionales)
    checked_price: float | None = None
    flexible_price: float | None = None
    for prod in (offer.get("extraProducts") or []):
        p = money_to_float((prod.get("priceBreakdown") or {}).get("total"))
        if prod.get("type") == "checkedInBaggage":
            checked_price = p
        elif prod.get("type") == "flexibleTicket":
            flexible_price = p

    # Identificador único de la oferta (viene ya armado desde Booking)
    flight_key = offer.get("flightKey") or offer.get("offerKeyToHighlight") or offer.get("token")

    return {
        "origin": origin.upper(),
        "destination": destination.upper(),
        "departDate": depart_date,
        "flightKey": flight_key,
        "airline": airline,
        "flightNumber": flight_number,
        "stops": stops,
        "durationMinutes": duration_min,
        "departTime": seg.get("departureTime"),
        "arrivalTime": seg.get("arrivalTime"),
        "currency": currency,
        "price": price,
        "priceRounded": price_rounded,
        "priceBeforeDiscount": price_before,
        "badges": badges,
        "fareName": (offer.get("brandedFareInfo") or {}).get("fareName"),
        "hasCheckedBaggageIncluded": has_checked_included,
        "checkedBaggagePrice": checked_price,
        "flexibleTicketPrice": flexible_price,
        "segments": segments,
        "token": offer.get("token"),
        "fetchedAt": utcnow(),
    }


def normalize_offers(
    payload: dict,
    origin: str,
    destination: str,
    depart_date: str,
) -> tuple[list[dict], dict | None]:
    """
    Normaliza TODAS las ofertas del payload.
    Devuelve (lista de docs normalizados, aggregation original).
    """
    offers, aggregation = extract_offers(payload)
    docs = []
    for offer in offers:
        doc = normalize_offer(offer, origin, destination, depart_date)
        if doc:
            docs.append(doc)
    return docs, aggregation