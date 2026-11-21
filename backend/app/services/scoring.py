"""
Funciones puras de scoring. Sin dependencias de DB ni de FastAPI.
Fáciles de testear unitariamente.
"""

MONTH_NAMES_ES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

IDEAL_TEMP = {
    "cold": (5, 15),
    "mild": (15, 24),
    "warm": (25, 32),
}


def weather_score(
    temp_max: float,
    temp_min: float,
    precip_mm: float,
    wind_kmh: float,
    pref: str,
) -> dict:
    """
    Score 0-100 según qué tan cómodo es el clima para la preferencia del usuario.
    Componentes:
      - Temperatura (55%): qué tan cerca está la media del rango ideal
      - Lluvia (35%): 0mm = perfecto, 4mm/día = 0
      - Viento (10%): <20km/h = perfecto
    """
    ideal = IDEAL_TEMP.get(pref, IDEAL_TEMP["mild"])
    avg = (temp_max + temp_min) / 2

    if ideal[0] <= avg <= ideal[1]:
        temp_score = 100.0
    else:
        dist = min(abs(avg - ideal[0]), abs(avg - ideal[1]))
        temp_score = max(0.0, 100 - dist * 8)

    rain_score = max(0.0, 100 - precip_mm * 25)
    wind_score = max(0.0, 100 - max(0.0, wind_kmh - 20) * 2)

    total = 0.55 * temp_score + 0.35 * rain_score + 0.10 * wind_score
    return {
        "total": round(total, 1),
        "temp_score": round(temp_score, 1),
        "rain_score": round(rain_score, 1),
        "wind_score": round(wind_score, 1),
    }


def price_score(price: float, budget: float) -> float:
    """
    Score 0-100 según qué tan bien encaja el precio en el presupuesto.
      precio=0        → 100
      precio=50% pbto → 75
      precio=100% pbto→ 50
      precio=150% pbto→ 25
      precio≥200% pbto→ 0
    """
    if budget <= 0:
        return 50.0
    ratio = price / budget
    if ratio <= 1:
        return round(100 - 50 * ratio, 1)
    return round(max(0.0, 50 * (2 - ratio)), 1)


def final_score(
    price_sc: float,
    weather_sc: float,
    w_price: float = 0.5,
    w_weather: float = 0.5,
) -> float:
    """Combina los dos scores con pesos."""
    return round(w_price * price_sc + w_weather * weather_sc, 1)