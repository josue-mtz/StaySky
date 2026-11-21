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


class FlightSummary(BaseModel):
    """Versión resumida para listados (sin segments ni token)."""
    origin: str
    destination: str
    departDate: str
    flightKey: str
    airline: dict
    flightNumber: str
    stops: int
    durationMinutes: int
    departTime: str
    arrivalTime: str
    currency: str
    price: float
    priceRounded: float | None = None
    priceBeforeDiscount: float | None = None
    badges: list[str] = []
    fareName: str | None = None
    hasCheckedBaggageIncluded: bool
    checkedBaggagePrice: float | None = None
    flexibleTicketPrice: float | None = None


class FlightsResponse(BaseModel):
    origin: str
    destination: str
    departDate: str
    source: str
    count: int
    aggregation: dict | None = None
    flights: list[FlightSummary]


class HotelSummary(BaseModel):
    """Versión resumida para listados."""
    destination: str
    checkinDate: str
    checkoutDate: str
    hotelId: int | None = None
    name: str
    stars: int | None = None
    reviewScore: float | None = None
    reviewCount: int | None = None
    currency: str
    price: float
    pricePerNight: float | None = None
    priceBeforeDiscount: float | None = None
    nights: int
    adults: int
    currencyMismatch: bool = False
    declaredCurrency: str | None = None


class HotelsResponse(BaseModel):
    destination: str
    checkinDate: str
    checkoutDate: str
    source: str
    count: int
    currencyMismatches: int = 0
    hotels: list[HotelSummary]