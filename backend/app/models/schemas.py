"""Modelos Pydantic: validan y documentan las respuestas de la API."""
from pydantic import BaseModel, Field


class City(BaseModel):
    iata: str = Field(..., min_length=3, max_length=3)
    name: str
    state: str
    country: str = "MX"
    lat: float
    lon: float
    timezone: str
    type: str = "ciudad"  # playa | ciudad | cultura


class DailyWeather(BaseModel):
    city: str
    date: str            # YYYY-MM-DD
    tempMaxC: float
    tempMinC: float
    tempMeanC: float
    precipitationMm: float
    windKmh: float
    weatherCode: int
    description: str


class WeatherResponse(BaseModel):
    city: str
    source: str          # "cache" | "api"
    count: int
    data: list[DailyWeather]