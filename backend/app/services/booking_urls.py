"""
Construye URLs públicas de Booking.com con la búsqueda prellenada.
No hay monetización: son enlaces directos al buscador oficial.
"""
from urllib.parse import urlencode


def build_flight_url(
    origin: str,
    destination: str,
    depart_date: str,
    adults: int = 1,
) -> str:
    """URL de Booking Flights con ruta y fecha prellenadas."""
    params = {
        "type": "ONEWAY",
        "origin": f"{origin.upper()}.AIRPORT",
        "destination": f"{destination.upper()}.AIRPORT",
        "depart": depart_date,
        "adults": str(adults),
        "cabinClass": "ECONOMY",
    }
    return f"https://www.booking.com/flights/search-results.html?{urlencode(params)}"


def build_hotel_url(
    city_name: str,
    checkin: str,
    checkout: str,
    adults: int = 2,
) -> str:
    """URL de Booking Hotels con destino y fechas prellenadas."""
    params = {
        "ss": city_name,
        "checkin": checkin,
        "checkout": checkout,
        "group_adults": str(adults),
        "no_rooms": "1",
    }
    return f"https://www.booking.com/searchresults.html?{urlencode(params)}"