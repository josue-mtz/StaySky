"""
Cliente HTTP para Booking.com Flights vía RapidAPI.

Las consultas externas deben pasar por la ruta de refresh, que exige
confirmación. La cuota y los límites del proveedor siguen aplicando.
"""
import httpx

from app.config import settings

# Endpoint de búsqueda de vuelos configurado para la integración Booking/RapidAPI.
FLIGHTS_ENDPOINT = "/api/v1/flights/searchFlights"


class BookingApiError(RuntimeError):
    """Error específico al llamar Booking. Se convierte en HTTP 502."""


async def search_flights(
    origin: str,
    destination: str,
    depart_date: str,
    adults: int = 1,
    currency: str = "MXN",
) -> dict:
    """
    Llama RapidAPI Booking Flights. Consume 1 request.
    Devuelve el JSON crudo tal cual lo da Booking (con data.flightOffers + data.aggregation).
    """
    if not settings.rapidapi_key:
        raise BookingApiError("RAPIDAPI_KEY no configurada en .env")

    url = f"https://{settings.rapidapi_host}{FLIGHTS_ENDPOINT}"
    headers = {
        "X-RapidAPI-Key": settings.rapidapi_key,
        "X-RapidAPI-Host": settings.rapidapi_host,
    }
    params = {
        "fromId": f"{origin.upper()}.AIRPORT",
        "toId": f"{destination.upper()}.AIRPORT",
        "departDate": depart_date,
        "adults": str(adults),
        "cabinClass": "ECONOMY",
        "currency_code": currency,
        "sort": "BEST",
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        raise BookingApiError(
            f"Booking respondió {exc.response.status_code}: {exc.response.text[:300]}"
        ) from exc
    except httpx.HTTPError as exc:
        raise BookingApiError(f"Error de red: {exc}") from exc