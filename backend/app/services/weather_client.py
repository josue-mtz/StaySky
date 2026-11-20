"""
Cliente de Open-Meteo Archive API.
Gratis, sin API key, sin rate limit relevante.
Docs: https://open-meteo.com/en/docs/historical-weather-api
"""
from datetime import date, timedelta

import httpx

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Traducción de códigos WMO a español simple (los que usa Open-Meteo)
WMO_DESC = {
    0: "Despejado", 1: "Mayormente despejado", 2: "Parcialmente nublado",
    3: "Nublado", 45: "Niebla", 48: "Niebla con escarcha",
    51: "Llovizna ligera", 53: "Llovizna moderada", 55: "Llovizna densa",
    61: "Lluvia ligera", 63: "Lluvia moderada", 65: "Lluvia fuerte",
    71: "Nieve ligera", 73: "Nieve moderada", 75: "Nieve fuerte",
    80: "Chubascos ligeros", 81: "Chubascos moderados", 82: "Chubascos fuertes",
    95: "Tormenta", 96: "Tormenta con granizo", 99: "Tormenta fuerte con granizo",
}


def _description(code: int | None) -> str:
    return WMO_DESC.get(code or 0, "Sin dato")


def clamp_archive_dates(start: str, end: str) -> tuple[str, str]:
    """
    Open-Meteo Archive solo cubre hasta ~5 días antes de hoy.
    Clampeamos para que nunca falle por fecha futura.
    """
    today = date.today()
    latest = today - timedelta(days=5)
    start_d = min(date.fromisoformat(start), latest)
    end_d = min(date.fromisoformat(end), latest)
    return start_d.isoformat(), end_d.isoformat()


async def fetch_open_meteo(
    lat: float, lon: float, start_date: str, end_date: str
) -> list[dict]:
    """
    Descarga clima diario desde Open-Meteo Archive.
    Devuelve lista de dicts listos para guardar en Mongo.
    """
    s, e = clamp_archive_dates(start_date, end_date)
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": s,
        "end_date": e,
        "daily": (
            "temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
            "precipitation_sum,wind_speed_10m_max,weather_code"
        ),
        "timezone": "auto",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(ARCHIVE_URL, params=params)
        resp.raise_for_status()
        payload = resp.json()

    daily = payload.get("daily") or {}
    times = daily.get("time") or []

    rows: list[dict] = []
    for i, d in enumerate(times):
        rows.append({
            "date": d,
            "tempMaxC": daily["temperature_2m_max"][i],
            "tempMinC": daily["temperature_2m_min"][i],
            "tempMeanC": daily["temperature_2m_mean"][i],
            "precipitationMm": daily["precipitation_sum"][i] or 0.0,
            "windKmh": daily["wind_speed_10m_max"][i] or 0.0,
            "weatherCode": daily["weather_code"][i] or 0,
            "description": _description(daily["weather_code"][i]),
        })
    return rows