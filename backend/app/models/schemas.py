"""Modelos Pydantic: validan y documentan las respuestas de la API."""
from pydantic import BaseModel, Field


class City(BaseModel):
    """Ciudad disponible en el catálogo, identificada por su código IATA."""

    iata: str = Field(..., min_length=3, max_length=3)
    name: str
    state: str
    country: str = "MX"
    lat: float
    lon: float
    timezone: str
    type: str = "ciudad"  # playa | ciudad | cultura


class DailyWeather(BaseModel):
    """Registro climático de un día para una ciudad."""

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
    """Respuesta con el origen y los registros diarios del clima."""

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
    baseFare: float | None = None
    taxes: float | None = None
    bookingUrl: str | None = None


class FlightsResponse(BaseModel):
    """Lista de vuelos cacheados para una ruta y fecha."""

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
    bookingUrl: str | None = None  


class HotelsResponse(BaseModel):
    """Lista de hoteles cacheados para destino y fechas de estancia."""

    destination: str
    checkinDate: str
    checkoutDate: str
    source: str
    count: int
    currencyMismatches: int = 0
    hotels: list[HotelSummary]


class WeatherSummary(BaseModel):
    """Resumen mensual del clima y su puntuación para la preferencia elegida."""

    month: str
    monthName: str
    tempMaxC: float
    tempMinC: float
    precipMm: float
    windKmh: float
    daysAnalyzed: int
    score: dict


class SearchRequest(BaseModel):
    """Parámetros validados para combinar vuelos, hoteles y clima."""

    origin: str = Field(..., min_length=3, max_length=3)
    destination: str = Field(..., min_length=3, max_length=3)
    departDate: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    budget: float = Field(15000, gt=0, description="Presupuesto total en MXN")
    weatherPref: str = Field("warm", pattern=r"^(cold|mild|warm)$")
    checkin: str | None = None
    checkout: str | None = None
    adults: int = Field(1, ge=1, le=9) 


class ScoredFlight(BaseModel):
    """Vuelo junto con sus puntuaciones de precio, clima y total."""

    flight: FlightSummary
    priceScore: float
    weatherScore: float
    finalScore: float


class ScoredHotel(BaseModel):
    """Hotel junto con sus puntuaciones de precio, clima y total."""

    hotel: HotelSummary
    priceScore: float
    weatherScore: float
    finalScore: float


class SearchResponse(BaseModel):
    """Recomendaciones y métricas devueltas por la búsqueda unificada."""

    origin: str
    destination: str
    destName: str
    departDate: str
    weatherPref: str
    budget: float
    flightBudget: float
    hotelBudget: float
    weather: WeatherSummary | None
    topFlights: list[ScoredFlight]
    topHotels: list[ScoredHotel]
    recommendedFlight: ScoredFlight | None
    recommendedHotel: ScoredHotel | None
    tripScore: float | None
    warnings: list[str] = []