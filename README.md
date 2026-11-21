# StaySky · Buscador de Viajes por Clima + Presupuesto

Integra vuelos, hoteles y clima histórico de México para ayudar a comparar
opciones de viaje según la ruta, preferencia climática y presupuesto.

## Interfaz
- El formulario solicita ruta, fechas, personas adultas, presupuesto y clima.
- El viaje redondo añade la fecha de regreso al enlace de vuelo de Booking.com; los precios de vuelo mostrados en StaySky corresponden a la salida.
- Los resultados presentan tres vuelos y seis hoteles destacados, con opción de desplegar más; el clima se muestra como estimación histórica, no como pronóstico.
- La interfaz adapta el tema claro/oscuro y cuenta con una página informativa en
  `http://localhost:8000/static/acerca.html`.
- Las imágenes de marca se encuentran en `frontend/assets/` (`banner.png` y
  `favicon.png`).

## Stack
- **Backend:** FastAPI 0.115 · Python 3.11
- **Base de datos:** MongoDB 7 (datos) + PostgreSQL 15 (metadata Airflow)
- **Orquestación:** Airflow 2.10.3 con LocalExecutor
- **Frontend:** HTML + Tailwind CSS (CDN)
- **APIs externas:** Open-Meteo Archive (gratis) · Booking.com vía RapidAPI

## Endpoints principales
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET  | `/health` | Estado API + Mongo |
| GET  | `/api/cities` | Catálogo de 10 destinos |
| GET  | `/api/weather/{iata}` | Clima histórico (con cache) |
| GET  | `/api/weather/{iata}/climate` | Promedios mensuales |
| GET  | `/api/flights/{o}/{d}?date=` | Vuelos cacheados |
| POST | `/api/flights/import-json` | Importar JSON (0 requests) |
| POST | `/api/flights/refresh` | ⚠️ Consume 1 request |
| GET  | `/api/flights/usage` | Cuota RapidAPI |
| GET  | `/api/hotels/{dest}?checkin=&checkout=` | Hoteles cacheados |
| GET  | `/api/hotels/{dest}/currency-audit` | Auditoría USD/MXN |
| POST | `/api/hotels/import-json` | Importar JSON (0 requests) |
| POST | `/api/search/` | **Búsqueda unificada con score** |
| GET  | `/api/admin/stats` | Estadísticas por pipeline |

## Cómo correr
1. Copia `.env.example` a `.env` y pon tu `RAPIDAPI_KEY`.
2. `docker compose up --build` (primera vez ~5 min).
3. Frontend: http://localhost:8000
4. Swagger: http://localhost:8000/docs
5. Airflow: http://localhost:8080 (`admin` / `admin`)

## DAGs de Airflow
- `weather_etl` (diario 6am) — refresca clima de 10 ciudades (gratis)
- `flights_etl` (diario 7am) — recomputa stats de vuelos (0 requests)
- `hotels_etl` (diario 8am) — recomputa stats + auditoría de moneda

## Decisiones de diseño
- **Cuota RapidAPI limitada a 20 requests/mes** → cache obligatorio en Mongo.
  Solo 8 requests consumidos en todo el proyecto.
- **Bug USD/MXN en Booking Hotels** → fuente de verdad en
  `priceBreakdown.grossPrice`, nunca en `property.currency`.
  15 de 20 hoteles de Cancún lo exhibían.
- **Postgres separado** solo para metadata de Airflow; MongoDB nunca
  se usa para estado interno de Airflow.