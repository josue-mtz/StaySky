"""
Normaliza el JSON crudo de Booking Hotels a documentos planos para Mongo.

    REGLA DE ORO DEL PROYECTO:
    Ignorar property.currency (a veces miente: dice USD pero es MXN).
    Usar SIEMPRE priceBreakdown.grossPrice.currency + .value.
"""
from datetime import date as date_cls

from app.db import utcnow


def _to_float(v) -> float | None:
    """Convierte a float sin importar si viene como int, str o None."""
    if v is None:
        return None
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def _calc_nights(checkin: str, checkout: str) -> int:
    """Devuelve la diferencia entre fechas, o cero si no se pueden parsear."""
    try:
        return (date_cls.fromisoformat(checkout) - date_cls.fromisoformat(checkin)).days
    except Exception:
        return 0


def normalize_hotel(
    hotel: dict,
    destination: str,
    checkin: str,
    checkout: str,
    adults: int = 2,
) -> dict | None:
    """
    Normaliza UNA propiedad. Devuelve None si le faltan datos esenciales.
    """
    prop = hotel.get("property") or {}
    if not prop or not prop.get("name"):
        return None

    # ---------- PRECIO (con fix del bug USD/MXN) ----------
    pb = prop.get("priceBreakdown") or {}
    gross = pb.get("grossPrice") or {}

    # Fuente de verdad
    price = _to_float(gross.get("value"))
    currency = gross.get("currency")          # ← la REAL

    # Auditoría: lo que declaraba el campo "de arriba"
    declared_currency = prop.get("currency")
    currency_mismatch = bool(
        declared_currency and currency and declared_currency != currency
    )

    if price is None:
        return None

    # Precio tachado (si hay descuento)
    strike = pb.get("strikethroughPrice") or {}
    price_before = _to_float(strike.get("value"))
    strike_currency = strike.get("currency")  # casi siempre igual a currency

    # ---------- NOCHES Y PRECIO POR NOCHE ----------
    nights = _calc_nights(checkin, checkout)
    price_per_night = round(price / nights, 2) if nights > 0 else None

    return {
        # Identificadores y fechas
        "destination": destination.upper(),
        "checkinDate": checkin,
        "checkoutDate": checkout,
        "hotelId": hotel.get("hotel_id"),

        # Datos del hotel
        "name": prop.get("name"),
        "lat": prop.get("latitude"),
        "lon": prop.get("longitude"),
        "stars": prop.get("propertyClass"),          # 1–5
        "reviewScore": prop.get("reviewScore"),      # típicamente 0–10
        "reviewCount": prop.get("reviewCount"),

        # Precio (post-fix)
        "currency": currency,                        # ← MXN esperado
        "price": price,                              # total por toda la estancia
        "pricePerNight": price_per_night,
        "priceBeforeDiscount": price_before,
        "nights": nights,
        "adults": adults,

        # Auditoría del bug
        "declaredCurrency": declared_currency,       # lo que decía property.currency
        "currencyMismatch": currency_mismatch,       # true si hubo bug
        "strikeCurrency": strike_currency,

        # Metadatos útiles (no se muestran prominentemente)
        "accessibilityLabel": hotel.get("accessibilityLabel"),

        # Timestamp
        "fetchedAt": utcnow(),
    }


def normalize_hotels(
    payload: dict,
    destination: str,
    checkin: str,
    checkout: str,
    adults: int = 2,
) -> tuple[list[dict], dict | list[dict] | None]:
    """
    Normaliza TODAS las propiedades del payload.
    Acepta tanto respuesta completa (con "data") como solo el payload.
    Devuelve (lista de docs, meta opcional).
    """
    data = payload.get("data", payload)
    hotels_raw = data.get("hotels") or []
    meta = data.get("meta")

    docs: list[dict] = []
    for h in hotels_raw:
        doc = normalize_hotel(h, destination, checkin, checkout, adults)
        if doc:
            docs.append(doc)

    return docs, meta