# StaySky: Buscador de viajes por clima y presupuesto

> **Estado del documento:** las marcas `[INSERTAR CAPTURA: ...]` son espacios reservados para agregar después las evidencias que están en el documento de Word. Completa también los datos de portada y revisa las reflexiones personales antes de entregar. Al final puedes exportarlo a PDF desde VS Code con una extensión de Markdown PDF.

---

## Documentación del proyecto final

**Proyecto final — Programación**

**Alumno:** Josué Uriel Martínez Ruíz
**Matrícula:** [Tu matrícula]
**Materia:** [Nombre de la materia]
**Profesor:** [Nombre del profesor]
**Fecha de entrega:** [Fecha]
**Última revisión técnica:** 22 de noviembre de 2026

## Resumen ejecutivo

StaySky es una aplicación web para consultar opciones de viaje en México a partir de una ruta, fechas, número de personas, presupuesto y preferencia climática. El sistema reúne clima histórico de Open-Meteo y ofertas de vuelos y hoteles normalizadas a partir de Booking.com vía RapidAPI. Un backend FastAPI consulta los datos almacenados en MongoDB, calcula puntuaciones de precio y clima y presenta una recomendación; Apache Airflow automatiza la actualización de clima y la generación de estadísticas.

La aplicación cuenta con una página principal de planificación y una página informativa “Acerca de StaySky”. La interfaz incluye temas claro y oscuro, un resumen visible de la búsqueda, recomendaciones de vuelos y alojamientos, visualizaciones mensuales del clima, y un pie de página con acceso a la página informativa. El diseño limita las llamadas a Booking mediante caché e importación de JSON. La versión documentada funciona con datos cacheados de rutas y fechas específicas; no es un metabuscador con disponibilidad garantizada para cualquier destino o fecha.

---

## Índice

[Resumen ejecutivo](#resumen-ejecutivo)
1. [Problema a solucionar](#1-problema-a-solucionar)
2. [Objetivos del proyecto](#2-objetivos-del-proyecto)
3. [Herramientas utilizadas](#3-herramientas-utilizadas)
4. [Arquitectura de la aplicación](#4-arquitectura-de-la-aplicación)
5. [Descripción del desarrollo](#5-descripción-del-desarrollo)
6. [Resultados](#6-resultados)
7. [Reflexión sobre la actividad](#7-reflexión-sobre-la-actividad)
8. [Reflexión sobre el curso y retroalimentación](#8-reflexión-sobre-el-curso-y-retroalimentación)
9. [Anexo: uso de IA como apoyo técnico y auditoría](#9-anexo-uso-de-ia-como-apoyo-técnico-y-auditoría)

---

## 1. Problema a solucionar

Planificar un viaje exige consultar varias fuentes: una para vuelos, otra para hospedaje y otra para el clima. Esto obliga al usuario a comparar resultados por separado y dificulta entender cuánto costaría el viaje completo o si las condiciones del destino coinciden con sus preferencias.

> *"¿A dónde puedo viajar con mi presupuesto, que tenga el clima que quiero, y qué tan buena es la oferta combinada de vuelo + hotel?"*

Las consecuencias de esta fragmentación son tangibles:

- El usuario compara precios sin considerar si el clima del destino es adecuado para su viaje (una playa barata en temporada de lluvias es una mala compra).
- El presupuesto se gestiona por separado para vuelo y hotel, cuando debería considerarse como un total.
- Los metabuscadores muestran decenas de resultados sin un criterio claro de *cuál es mejor para este usuario*.

**StaySky** integra vuelos, alojamientos y clima histórico en una sola aplicación. Para una ruta, fechas, cantidad de personas, presupuesto y preferencia climática seleccionados por el usuario, presenta opciones disponibles en la caché y calcula puntuaciones explicables que ayudan a compararlas. En esta versión el usuario elige el destino: el sistema no compara automáticamente todos los destinos del catálogo ni garantiza disponibilidad en fechas sin datos cacheados.

---

## 2. Objetivos del proyecto

### Objetivo general

Construir una aplicación web funcional y contenerizada con Docker que integre vuelos, hoteles y clima histórico para evaluar y recomendar opciones de viaje a destinos mexicanos según el presupuesto y la preferencia climática indicados por el usuario, con datos persistidos en MongoDB y procesos de actualización orquestados con Airflow.

### Objetivos específicos

1. **Integrar tres fuentes de datos** heterogéneas (Open-Meteo, Booking.com Flights, Booking.com Hotels) mediante un backend en **FastAPI**.
2. **Persistir los datos** en **MongoDB 7**, modelando las colecciones con índices que soporten consultas por ruta, fecha y destino.
3. **Diseñar una función de scoring** que combine precio y clima en un puntaje único (0–100) interpretable por el usuario final.
4. **Orquestar la actualización de datos y estadísticas** con **Apache Airflow**, mediante DAGs programados y re-ejecutables.
5. **Contenerizar todo el stack** (6 servicios) con **Docker Compose**, garantizando reproducibilidad.
6. **Aplicar reglas de calidad de datos** que resuelvan inconsistencias reales detectadas en las fuentes (específicamente, el bug USD/MXN en Booking Hotels).
7. **Gestionar las llamadas externas** a RapidAPI con caché, importación local y confirmación explícita de refresh. La cuota y los cargos siguen dependiendo del plan del proveedor; StaySky no aplica un tope local.

---

## 3. Herramientas utilizadas

| Categoría | Herramienta | Versión | Rol en el proyecto |
|---|---|---|---|
| Backend | **FastAPI** | 0.115.0 | Framework HTTP + documentación OpenAPI automática |
| Servidor ASGI | **Uvicorn** | 0.32.0 | Servidor con hot-reload |
| Lenguaje | **Python** | 3.11 | Backend, DAGs, scripts |
| Driver Mongo | **Motor** | 3.6.0 | Cliente asíncrono oficial de MongoDB |
| Validación | **Pydantic** + **pydantic-settings** | 2.9.2 / 2.6.1 | Modelos y lectura de `.env` |
| Cliente HTTP | **httpx** | 0.27.2 | Llamadas a Open-Meteo y RapidAPI |
| Base de datos principal | **MongoDB** | 7.x (imagen `mongo:7`; verificada localmente con 7.0.48) | Persistencia de vuelos, hoteles, clima y ciudades |
| Base de datos de orquestación | **PostgreSQL** | 15 | Metadata interna de Airflow (única función) |
| Orquestador | **Apache Airflow** | 2.10.3 (Python 3.11) | Automatización diaria de ingesta y recomputo de stats |
| Frontend | **HTML5 + Tailwind CSS** (vía CDN) | 3.x | Páginas estáticas de planificación y “Acerca de”, sin proceso de build |
| Contenedores | **Docker** + **Docker Compose** | — | 6 servicios orquestados |
| API de clima | **Open-Meteo Archive** | — | Histórico diario, gratuito, sin API key |
| API de vuelos/hoteles | **Booking.com** vía **RapidAPI** | — | Consultas externas sujetas a la cuota y condiciones del plan del proveedor |
| Editor | **Visual Studio Code** | — | IDE principal |
| Control de versiones | **Git** (local) | — | Historial de desarrollo |

### Decisiones tecnológicas relevantes

- **MongoDB para los datos del dominio:** las respuestas de Booking contienen estructuras anidadas (`flightOffers[].segments[].legs[]`, `hotels[].property.priceBreakdown`). MongoDB permite conservar esos documentos y consultarlos sin descomponerlos en varias tablas.
- **PostgreSQL para Airflow:** PostgreSQL guarda la metadata interna del orquestador; MongoDB se reserva para los datos de StaySky. En esta configuración Airflow utiliza `LocalExecutor` y PostgreSQL.
- **Tailwind vía CDN, sin React ni Vite:** el alcance del proyecto no justifica un sistema de build. HTML plano + Tailwind CDN servido por `StaticFiles` de FastAPI resultó suficiente para la página de planificación y la página informativa.

---

## 4. Arquitectura de la aplicación

### 4.1. Diagrama de bloques

```
┌──────────────────────────────────────────────────────────────┐
│  FRONTEND · HTML + Tailwind (CDN)                             │
│  Servido por FastAPI en http://localhost:8000                 │
│  · Planificación: ruta, fechas, personas, presupuesto y clima  │
│  · Resultados: viaje recomendado, clima, vuelos y alojamientos│
│  · Página Acerca de, tema claro/oscuro y pie de página        │
└───────────────────────┬──────────────────────────────────────┘
                        │ fetch()
┌───────────────────────▼──────────────────────────────────────┐
│  BACKEND · FastAPI (contenedor: staysky_backend)              │
│                                                               │
│  Rutas:                                                       │
│  · /api/cities                · /api/weather/{iata}          │
│  · /api/flights/{o}/{d}       · /api/hotels/{dest}           │
│  · /api/flights/import-json   · /api/hotels/import-json      │
│  · /api/flights/refresh ⚠️    · /api/hotels/refresh ⚠️       │
│  · /api/flights/usage         · /api/admin/stats             │
│  · /api/search/  ← endpoint unificado con scoring             │
│  · /api/admin/rebuild-stats   · /api/admin/pipeline-runs     │
│                                                               │
│  Servicios internos:                                          │
│  · weather_client.py  → Open-Meteo Archive                   │
│  · booking_client.py  → RapidAPI Booking                     │
│  · flights_normalizer.py · hotels_normalizer.py              │
│  · scoring.py (funciones puras, testeables)                  │
└───────────────────────┬──────────────────────────────────────┘
                        │
        ┌───────────────┴────────────────┐
        │                                │
┌───────▼──────────┐         ┌───────────▼──────────────────────┐
│  MONGODB 7       │         │  AIRFLOW 2.10.3                   │
│  staysky_mongo   │         │  staysky_airflow_web   (:8080)    │
│                  │         │  staysky_airflow_sched            │
│  Colecciones:    │         │  staysky_airflow_init (run once)  │
│  · cities        │         │                                    │
│  · flights       │         │  DAGs:                             │
│  · hotels        │         │  · weather_etl   (diario 06:00)   │
│  · weather       │         │  · flights_etl   (diario 07:00)   │
│  · searches*     │         │  · hotels_etl    (diario 08:00)   │
│  · pipeline_stats│         │                                    │
│  · pipeline_runs │         │  Metadata: PostgreSQL 15           │
│  · api_usage     │         │  (staysky_postgres, aislada)       │
│  · flight_aggregations      │                                    │
└──────────────────┘         └────────────────────────────────────┘
```

Las cinco colecciones iniciales son `cities`, `flights`, `hotels`, `weather` y `searches`. Las colecciones auxiliares se usan para cuota, agregaciones y auditoría. `searches` se crea en MongoDB, pero la búsqueda unificada actual no persiste cada consulta en esa colección.

### 4.2. Flujo de una búsqueda unificada

```
Usuario llena formulario (origen, destino, fechas, adultos, presupuesto, clima)
       │
       ▼
POST /api/search/  {origin, destination, departDate, checkout, adults, budget, weatherPref}
       │
       ├─► Busca ciudad en `cities` (por IATA)
       ├─► Toma el mes de departDate → busca clima típico de ese mes
       │     en `weather` (agregación mensual sobre histórico 2023)
       ├─► weather_score = f(temp, lluvia, viento, weatherPref)   → 0-100
       ├─► Reparte presupuesto: 30% vuelo / 70% hotel
       ├─► Vuelos cacheados en `flights` filtrados por (origen, destino, fecha)
       │     price_score = f(precio, flightBudget)                → 0-100
       │     final_score = 0.5 · price + 0.5 · weather           → 0-100
       ├─► Hoteles cacheados en `hotels` filtrados por (destino, checkin, checkout)
       │     price_score = f(precio, hotelBudget)
       │     final_score = 0.5 · price + 0.5 · weather
       └─► Devuelve: top 3 vuelos + top 3 hoteles + viaje recomendado
             y tripScore (promedio del mejor vuelo y hotel)
```

En el formulario, el regreso es opcional; al elegir viaje redondo, se usa esa fecha como salida del hospedaje y se incluye en el enlace de vuelo a Booking.com. Los precios de vuelos que StaySky muestra desde su caché corresponden únicamente a la salida. Si no se especifica regreso, la interfaz propone una estancia de tres noches para consultar hoteles.

### 4.3. Principio de diseño clave: **caché obligatorio**

Durante el desarrollo, el plan Basic de Booking vía RapidAPI reportaba una cuota de **20 requests al mes**. Esa cuota pertenece al proveedor y puede cambiar según el plan. Para evitar llamadas innecesarias:

- Los endpoints `GET /api/flights/{o}/{d}` y `GET /api/hotels/{dest}` **siempre leen de MongoDB**, nunca de RapidAPI.
- Existen dos formas de poblar Mongo:
  - `POST /api/flights/import-json` (o `/api/hotels/import-json`) → sube un JSON ya descargado, **0 requests**.
  - `POST /api/flights/refresh?confirm=yes` y `POST /api/hotels/refresh?confirm=yes` → cada consulta directa puede consumir cuota del proveedor, requiere confirmación y se contabiliza en el uso compartido cuando la respuesta externa es exitosa.
- Para refresh de hoteles hay `dest_id` de Booking confirmados para Cancún (`CUN`) y Oaxaca (`OAX`); otros destinos requieren proporcionar su identificador.
- El refresh de vuelos solicita importes en MXN (`currency_code=MXN`) para que la puntuación sea comparable con el presupuesto capturado en MXN.
- Los DAGs de Airflow no hacen llamadas normales a Booking. El refresh opcional de vuelos está apagado por configuración; el paso de refresh de hoteles está deshabilitado en el código actual. Sí actualizan clima con Open-Meteo y recomputan estadísticas usando la caché.
- StaySky no impone un máximo local de llamadas: `/api/flights/usage` informa el uso registrado, pero la cuota, posibles cargos y bloqueos los determina RapidAPI. Los rechazos del proveedor pueden no quedar registrados como respuestas exitosas en el contador local.

**Fotografía histórica del 20 de noviembre de 2026:** `/api/flights/usage` reportó **8 requests exitosos registrados** y el plan externo reportado entonces tenía una cuota de 20. Ese contador no determina la cuota actual del proveedor.

### 4.4. Endpoints principales

| Método | Endpoint | Función |
|---|---|---|
| `GET` | `/health` | Comprueba que FastAPI responde y reporta la conexión con MongoDB. |
| `GET` | `/api/cities` | Lista las ciudades del catálogo; `POST /api/cities/seed` las crea o actualiza. |
| `GET` | `/api/weather/{iata}` | Consulta clima histórico y usa la caché si tiene cobertura suficiente; acepta `start_date`, `end_date` y `refresh`. |
| `GET` | `/api/weather/{iata}/climate` | Devuelve promedios mensuales del clima cacheado. |
| `GET` | `/api/flights/{origin}/{destination}?date=YYYY-MM-DD` | Lee vuelos cacheados, ordenados por precio. |
| `GET` | `/api/flights/{origin}/{destination}/dates` | Lista fechas con vuelos disponibles en caché. |
| `POST` | `/api/flights/usage/seed?used_before=N` | Registra uso externo previo para el contador informativo. |
| `POST` | `/api/flights/import-json` | Importa ofertas de un JSON sin llamar a RapidAPI. |
| `POST` | `/api/flights/refresh` | Consulta Booking; requiere `confirm=yes`. RapidAPI aplica su cuota externa; StaySky no tiene tope local. |
| `GET` | `/api/flights/usage` | Informa uso de API registrado; `limit` y `remaining` son `null` porque no existe tope local. |
| `GET` | `/api/hotels/{destination}` | Lee hoteles cacheados para `checkin` y `checkout`. |
| `GET` | `/api/hotels/{destination}/dates` | Lista periodos de hospedaje disponibles en caché. |
| `GET` | `/api/hotels/{destination}/currency-audit` | Resume inconsistencias de moneda detectadas. |
| `POST` | `/api/hotels/import-json` | Importa hoteles de un JSON sin consumir cuota. |
| `POST` | `/api/hotels/refresh` | Consulta Booking; requiere `confirm=yes`. RapidAPI aplica su cuota externa; StaySky no tiene tope local. |
| `POST` | `/api/search/` | Combina clima, vuelos, hoteles y puntuaciones en una respuesta. |
| `POST` / `GET` | `/api/admin/rebuild-stats`, `/api/admin/stats` | Reconstruye y consulta estadísticas agregadas. |
| `GET` | `/api/admin/pipeline-runs` | Consulta el historial de ejecuciones de los pipelines. |

Swagger UI, con los modelos y parámetros de la API, está disponible en `http://localhost:8000/docs`.

### 4.5. Ejecución local

1. Copiar `.env.example` a `.env` y configurar `RAPIDAPI_KEY` para habilitar llamadas reales a Booking. Las consultas cacheadas y la importación JSON no necesitan consumir esa cuota.
2. Desde la carpeta raíz del proyecto, ejecutar `docker compose up --build`.
3. Abrir la aplicación en `http://localhost:8000`, Swagger en `http://localhost:8000/docs` y Airflow en `http://localhost:8080` (usuario/contraseña local: `admin` / `admin`).
4. Para revisar MongoDB: `docker exec -it staysky_mongo mongosh`, después `use staysky` y `show collections`.

Las credenciales de ejemplo incluidas en Compose son solo para desarrollo local. No publiques `.env`, claves de RapidAPI ni credenciales de demostración en un repositorio público o despliegue expuesto.

---

## 5. Descripción del desarrollo

El plan original se organizó en **7 fases incrementales**. Se realizaron las fases 1–5 y 7; la fase 6 (comparador automático de múltiples destinos) se dejó fuera del alcance. A continuación se documentan los componentes construidos y los errores identificados durante el desarrollo.

### 5.1. Fase 1 — Esqueleto del stack con Docker

**Objetivo:** levantar MongoDB y FastAPI en contenedores, con frontend estático y verificación de salud.

**Actividades:**
- Creación de `docker-compose.yml` con dos servicios (`mongo`, `backend`).
- Estructura de carpetas: `backend/app/{routes,services,models}`, `frontend/`, `mongo/`, `docs/`.
- Backend mínimo con endpoints `/health` (ping a Mongo) y `/` (sirve `index.html`).
- Frontend con formulario vacío y Tailwind vía CDN, con indicador de conexión en la esquina.
- Script `mongo/init.js` para crear colecciones automáticamente la primera vez.

**Verificación:**
- `docker compose up --build` levanta 2 contenedores.
- `/health` responde `{"status":"ok","mongo":"connected"}`.
- Frontend en `localhost:8000` muestra indicador verde.

**Decisión de diseño:** montar `./backend/app` y `./frontend` como volúmenes para que el hot-reload de Uvicorn funcione sin reconstruir la imagen.

**Capturas:**
- [INSERTAR CAPTURA: 01_docker_ps.png]
- [INSERTAR CAPTURA: 02_frontend.png]
- [INSERTAR CAPTURA: 03_swagger.png]
- [INSERTAR CAPTURA: 04_mongo.png]

---

### 5.2. Fase 2 — Catálogo de ciudades y clima histórico

**Objetivo:** sembrar las 10 ciudades mexicanas, integrar Open-Meteo Archive y cachear el clima.

**Actividades:**
- Catálogo de 10 destinos mexicanos en `mongo/init.js` (CUN, MEX, GDL, PVR, SJD, MID, HUX, ZIH, MTY, OAX) con lat/lon, timezone y tipo (playa/ciudad/cultura).
- `services/weather_client.py`: cliente de Open-Meteo con función `clamp_archive_dates` para evitar errores por fechas futuras (Archive solo cubre hasta 5 días antes de hoy).
- Endpoints: `/api/cities`, `/api/cities/seed`, `/api/weather/{iata}`, `/api/weather/{iata}/climate`.
- Frontend: selector de destino y panel de 12 tarjetas mensuales.

**Errores encontrados y solución:**

> **Error 1:** Al llamar `/api/weather/CUN` la API fallaba con 500. **Causa:** el router de clima estaba definido en `weather.py` pero **no registrado en `main.py`** con `app.include_router(weather.router)`. **Solución:** añadir la línea faltante.

> **Error 2:** Tras registrar el router, la respuesta fallaba con 422 de Pydantic. **Causa:** el modelo `WeatherResponse` exige un campo `city` en cada fila de `data`, pero Open-Meteo no devuelve ese campo (devuelve `date`, `tempMaxC`, etc.). **Solución:** en `routes/weather.py`, inyectar `city: iata` al construir cada fila antes de validar y persistir.

**Verificación:**
- `/api/cities` devuelve las 10 ciudades.
- `/api/weather/CUN` la primera vez responde `source:"api"` con 365 días; la segunda vez responde `source:"cache"` inmediatamente (viene de Mongo).
- `/api/weather/CUN/climate` devuelve 12 meses agregados.

**Capturas:**
- [INSERTAR CAPTURA: 05_swagger_fase2.png]
- [INSERTAR CAPTURA: 06_clima_cancun.png]
- [INSERTAR CAPTURA: 07_clima_loscabos.png]
- [INSERTAR CAPTURA: 08_mongo_weather.png]

---

### 5.3. Fase 3 — Vuelos con caché y consulta directa confirmada

**Objetivo:** integrar vuelos de Booking, usando caché para las búsquedas normales y separando las consultas directas a RapidAPI.

**Actividades:**
- `services/booking_client.py`: cliente HTTP a RapidAPI Booking Flights, con manejo de errores `BookingApiError`.
- `services/flights_normalizer.py`: transforma `flightOffers[]` de Booking a documentos planos para Mongo. Incluye:
  - Conversión de precios `{units, nanos}` → float (`units + nanos * 1e-9`).
  - Cálculo de escalas desde `len(legs) - 1`.
  - Conversión de `totalTime` (segundos) → minutos.
  - Extracción de aerolínea, número de vuelo, badges (`CHEAPEST`/`BEST`/`FASTEST`), equipaje incluido.
- Endpoints:
  - `GET /api/flights/{origin}/{destination}?date=` → **lee Mongo, 0 requests**.
  - `GET /api/flights/{origin}/{destination}/dates` → consulta fechas con vuelos cacheados.
  - `POST /api/flights/import-json` → carga JSON offline, **0 requests**.
  - `POST /api/flights/refresh?confirm=yes` → consulta Booking tras confirmación explícita. StaySky no aplica tope local; la cuota y posibles cargos siguen sujetos al proveedor.
  - `GET /api/flights/usage` → informa el uso externo registrado, sin calcular requests restantes de un plan.
- Frontend: tarjetas de vuelos con aerolínea, horarios, duración, badges y precio.

**Estrategia anti-quema implementada:**

| Acción | Costo | Cuándo |
|---|---|---|
| Importar un JSON de vuelos ya descargado | 0 requests | Al preparar la caché |
| Desarrollo y debugging de normalizer | 0 requests | Toda la fase |
| Llamada real a Booking para una ruta adicional (MEX→SJD) | Sujeta al plan de RapidAPI | Opcional y requiere `confirm=yes` |

**Verificación:**
- En la caché consultada actualmente hay **30 vuelos: 15 para MEX→CUN y 15 para MEX→SJD**, todos para el 12 de marzo de 2027.
- En la fotografía histórica de uso, `/api/flights/usage` reportó 8 respuestas exitosas registradas (7 previas y 1 registrada por el sistema). El endpoint ya no informa requests restantes ni bloquea por un límite local.
- Frontend muestra las tarjetas al buscar MEX→CUN con fecha 2027-03-12.

**Capturas:**
- [INSERTAR CAPTURA: 09_import_json.png]
- [INSERTAR CAPTURA: 10_flights_cun.png]
- [INSERTAR CAPTURA: 11_usage_counter.png]
- [INSERTAR CAPTURA: 12_mongo_flights.png]

---

### 5.4. Fase 4 — Hoteles y el fix del bug USD/MXN

**Objetivo:** integrar hoteles y resolver la inconsistencia de moneda detectada en el JSON de Booking.

**Bug de calidad de datos detectado:** en varias propiedades del JSON de prueba, `property.currency` indicaba `"USD"`, mientras que `priceBreakdown.grossPrice.currency` y los valores numéricos estaban en **`"MXN"`**. Si el desarrollador confiaba en el campo `currency` de nivel superior, mostraría **$6,064 USD** en lugar de **$6,064 MXN** (≈ 17× de error).

**Regla aplicada:**
1. **Fuente de verdad:** `priceBreakdown.grossPrice.currency` + `.value` — SIEMPRE.
2. **Auditoría:** se guarda `declaredCurrency` (lo que decía `property.currency`) y `currencyMismatch` (booleano) en cada documento para trazabilidad.
3. **Nunca** se usa `property.currency` para mostrar precios en la UI.

**Actividades:**
- `services/hotels_normalizer.py`: normalizador con la regla del fix, cálculo de `pricePerNight` y `nights`.
- Endpoints: `GET /api/hotels/{dest}` consulta la caché; `GET /api/hotels/{dest}/dates` lista fechas disponibles; `GET /api/hotels/{dest}/currency-audit` resume inconsistencias; `POST /api/hotels/import-json` importa sin consumir cuota; `POST /api/hotels/refresh` permite una consulta real a RapidAPI con confirmación.
- Frontend: las tarjetas muestran estrellas, calificación, precio por noche y total. Se presentan dos opciones económicas, dos cercanas al precio intermedio y dos mejor valoradas; las demás se pueden desplegar.

**Errores encontrados y solución:**

> **Error 3:** Al importar el JSON de hoteles, la operación guardaba los 20 hoteles pero luego fallaba con error 500. **Causa:** el campo `meta` del JSON viene como **lista** en algunos payloads, no como objeto, y el normalizador asumía `meta.get("totalCount")`. **Solución:** validar el tipo antes de acceder (`isinstance(meta, dict)`).

> **Error 4:** En el frontend, el botón "Buscar" no ejecutaba `loadHotels` y mostraba los paneles vacíos. **Causa:** un problema de alcance (scope) en JavaScript — la función `loadHotels` estaba definida dentro de un bloque pero el handler del form la llamaba antes de que existiera en el scope global. **Solución:** mover `loadHotels` fuera del bloque anidado y asegurar que esté en el scope del `<script>` principal.

**Verificación:**
- 20 hoteles guardados en `hotels` para CUN (2027-03-12 → 2027-03-15).
- `/api/hotels/CUN/currency-audit` revela **15 de 20 hoteles (75%)** con `currencyMismatch: true`. **Este dato es evidencia directa del bug detectado y corregido.**
- `/api/flights/usage` sigue en 8 (import no consumió requests).

**Capturas:**
- [INSERTAR CAPTURA: 13_import_hotels.png]
- [INSERTAR CAPTURA: 14_currency_audit.png]
- [INSERTAR CAPTURA: 15_frontend_full.png]
- [INSERTAR CAPTURA: 16_mongo_hotels.png]

---

### 5.5. Fase 5 — Scoring y endpoint unificado de búsqueda

**Objetivo:** implementar la función de scoring que combina precio y clima, y exponer `/api/search/` como el endpoint estrella del proyecto.

**Actividades:**
- `services/scoring.py`: tres funciones puras y testeables:
  - `weather_score(temp_max, temp_min, precip_mm, wind_kmh, pref)` → 0-100.
    - Componentes: temperatura (55%, penaliza lejanía del rango ideal), lluvia (35%, penaliza mm/día), viento (10%, penaliza >20 km/h).
    - Rangos ideales por preferencia: `cold` (5-15°C), `mild` (15-24°C), `warm` (25-32°C).
  - `price_score(price, budget)` → 0-100, con curva lineal: 100 si es gratis, 50 si el precio es igual al presupuesto, 0 si es ≥ 2× el presupuesto.
  - `final_score(price_sc, weather_sc, w_price=0.5, w_weather=0.5)` → combina precio y clima al 50%.
- `routes/search.py`: `POST /api/search/` recibe origen, destino, fecha de salida, presupuesto, preferencia climática y, opcionalmente, número de adultos y fechas de hospedaje (`checkin`, `checkout`). Devuelve el clima mensual típico, hasta 3 vuelos y 3 hoteles ordenados por puntuación, además del vuelo y hotel recomendados.
- `tripScore` es el promedio de la puntuación del mejor vuelo y la del mejor hotel; por eso depende de los datos cacheados, la fecha, el presupuesto y la preferencia climática.
- Frontend: tarjeta con gradiente índigo-violeta-naranja para el viaje recomendado; los paneles de vuelos y alojamientos aparecen en dos columnas cuando el ancho de pantalla lo permite. El formulario envía `adults` y el `checkout` elegido (o tres noches por defecto).

**Verificación (evidencia de que el scoring funciona):**

| Caso | Destino | Clima pref. | Trip Score |
|---|---|---|---|
| 1 | CUN (Cancún) | cálido | **85.3** |
| 2 | CUN (Cancún) | frío | **61.4** |

La diferencia de **23.9 puntos** entre ambos casos demuestra que la función **discrimina correctamente** y no es arbitraria: Cancún es objetivamente un destino cálido, y declararlo "frío" reduce drásticamente la adecuación climática.

**Capturas:**
- [INSERTAR CAPTURA: 17_swagger_search.png]
- [INSERTAR CAPTURA: 18_score_cun_warm.png]
- [INSERTAR CAPTURA: 19_score_cun_cold.png]
- [INSERTAR CAPTURA: 20_score_sjd_mild.png]
- [INSERTAR CAPTURA: 21_usage_still_8.png]

---

### 5.6. Fase 6 — (omitida deliberadamente)

Se decidió **saltar** esta fase del plan original (comparador multi-destino) para priorizar la orquestación con Airflow, que tiene mayor peso en los entregables del curso. El alcance funcional del proyecto ya quedaba completo con la Fase 5.

---

### 5.7. Fase 7 — Airflow y automatización de la ingesta

**Objetivo:** añadir Airflow para automatizar la actualización diaria de clima y el recomputo de estadísticas, **sin consumir requests** de RapidAPI.

**Actividades:**
- Nuevos servicios en `docker-compose.yml`:
  - `postgres:15` — metadata de Airflow.
  - `airflow-init` — inicializa DB y usuario `admin`, corre una vez y termina.
  - `airflow-webserver` — UI en `localhost:8080`.
  - `airflow-scheduler` — ejecuta los DAGs.
- `airflow/Dockerfile`: imagen `apache/airflow:2.10.3-python3.11` + `httpx`.
- Tres DAGs:
  - `weather_etl` (cron `0 6 * * *`): solicita datos históricos de las 10 ciudades a Open-Meteo.
  - `flights_etl` (cron `0 7 * * *`): recomputa `pipeline_stats` de vuelos desde Mongo (0 requests). El refresh real a Booking está **desactivado por defecto** con `STAYSKY_CONFIRM_REFRESH=false`.
  - `hotels_etl` (cron `0 8 * * *`): recomputa `pipeline_stats` de hoteles y ejecuta la auditoría USD/MXN (0 requests).
- El endpoint `POST /api/admin/rebuild-stats?scope=flights|hotels|all` agrega con `$group` de Mongo y persiste en `pipeline_stats`; `GET /api/admin/stats` permite consultarlas.
- Colección `pipeline_runs` para auditar ejecuciones.

**Errores encontrados y solución:**

> **Error 5:** El contenedor `airflow-init` fallaba con código de salida 1 **al reiniciar el stack** (`docker compose down && up`). **Causa:** el comando `airflow users create --username admin` fallaba porque el usuario ya existía en Postgres de una ejecución anterior, abortando el comando con `exit 1`, y como `airflow-webserver` dependía de `service_completed_successfully` de `airflow-init`, **no arrancaba**. **Solución:** envolver el comando en `( ... || echo "ya existe, continuando") &&` para que un fallo del `users create` **no aborte** el init.

> **Error 6:** Al consultar `db.stats.countDocuments()` en `mongosh`, Mongo respondía `TypeError: db.stats.countDocuments is not a function`. **Causa:** `stats` es un **comando interno reservado de MongoDB**; `db.stats` no es una colección sino el método de estadísticas del servidor. La colección sí existía y era accesible con `db.getCollection("stats")`. **Solución:** renombrar la colección a `pipeline_stats` para evitar la colisión, y repoblar ejecutando nuevamente los DAGs `flights_etl` y `hotels_etl`.

**Verificación:**
- Los tres DAGs se ejecutaron durante las pruebas desde la UI de Airflow.
- En la última consulta de la API se observaron **6** registros en `/api/admin/pipeline-runs`; el número aumenta con nuevas ejecuciones.
- `db.pipeline_stats.countDocuments()` = **3** (2 rutas de vuelo + 1 destino hotelero).
- `db.getCollection("pipeline_stats").find({type:"hotel"})` devuelve `{key: 'hotel:CUN-2027-03-12-2027-03-15', count: 20, minPrice: 2416.17}`.
- `/api/flights/usage` registró **8 respuestas externas exitosas** en la revisión del 20 de noviembre de 2026; el límite de 20 correspondía a la cuota externa del plan reportada entonces, no a un bloqueo local de StaySky.

**Capturas:**
- [INSERTAR CAPTURA: 22_airflow_dags.png]
- [INSERTAR CAPTURA: 23_airflow_grid.png]
- [INSERTAR CAPTURA: 24_airflow_logs.png]
- [INSERTAR CAPTURA: 25_airflow_flights_logs.png]
- [INSERTAR CAPTURA: 26_docker_ps_full.png]
- [INSERTAR CAPTURA: 27_mongo_pipeline_runs.png]
- [INSERTAR CAPTURA: 28_usage_still_8.png]

---

### 5.8. Cambios de nomenclatura

Durante el desarrollo el proyecto cambió de nombre: de "Buscador de vuelos/clima" (working title) a **StaySky**. Se renombró:
- Base de datos: `vuelos_clima` → `staysky`.
- Contenedor Mongo: `vuelos_mongo` → `staysky_mongo`.
- Carpeta raíz del proyecto: `proyecto-vuelos-clima` → `StaySky`.

Este cambio se propagó a `.env`, `docker-compose.yml`, `mongo/init.js` y todos los módulos del backend.

### 5.9. Resumen cuantitativo del desarrollo

Las cifras de datos y ejecuciones son una **fotografía del entorno local consultado el 20 de noviembre de 2026**; pueden cambiar al importar información o ejecutar nuevos pipelines.

| Métrica | Valor |
|---|---|
| Fases del plan realizadas | 6 de 7 (fases 1–5 y 7; fase 6 omitida) |
| Errores encontrados y resueltos | 7 documentados |
| Servicios definidos en Docker Compose | 6 |
| Colecciones iniciales de dominio | 5 (`cities`, `flights`, `hotels`, `weather`, `searches`) |
| Colecciones auxiliares utilizadas | `pipeline_stats`, `pipeline_runs`, `api_usage` y `flight_aggregations` |
| Ciudades sembradas | 10 |
| Vuelos cacheados | 30 (15 para MEX→CUN y 15 para MEX→SJD, fecha 2027-03-12) |
| Hoteles cacheados | 20 (CUN, 2027-03-12 a 2027-03-15) |
| Registros de clima consultados | 365 para CUN durante 2023 |
| Respuestas exitosas de RapidAPI registradas | 8 en la fotografía del 20 de noviembre de 2026 (la cuota del plan externo reportada entonces era 20) |
| DAGs de Airflow definidos | 3 |
| Ejecuciones registradas en `pipeline_runs` | 6 al momento de la revisión |
| Agregaciones en `pipeline_stats` | 3 (2 rutas de vuelo y 1 consulta de hoteles) |

### 5.10. Mejoras finales de interfaz y página informativa

Después de completar las funciones de búsqueda se añadieron ajustes de presentación y claridad para el usuario:

- **Error 7:** el JavaScript del frontend no iniciaba y mostraba `Unexpected token ')'` porque faltaba cerrar la función `renderHotelCard`. Se corrigió el cierre; después se verificó la carga de ciudades y los flujos de búsqueda. También se reforzó el manejo de errores para que un fallo al cargar el clima no impida mostrar vuelos y hoteles.
- El formulario inicia sin ciudades, fechas, presupuesto, cantidad de adultos ni clima preseleccionados. Muestra indicaciones de entrada y valida los campos requeridos; permite elegir de 1 a 9 adultos.
- Se agregó la opción de viaje redondo con una fecha de regreso posterior a la salida. Esta fecha se envía como `checkout` para buscar hospedaje y se agrega al enlace de vuelo de Booking.com. Los precios de vuelos presentados por StaySky siguen siendo los cacheados para la fecha de salida, no una tarifa de ida y vuelta.
- El resumen de búsqueda conserva en la barra superior la ruta, las fechas y el número de personas. El control de tema claro/oscuro queda alineado a la derecha y guarda la preferencia en el navegador.
- En los resultados se muestran inicialmente los tres vuelos más económicos y seis hoteles destacados (dos económicos, dos de precio intermedio y dos mejor valorados); los botones permiten desplegar el resto. Se indica que el usuario debe confirmar disponibilidad, servicios y precio final en Booking.com.
- Se agregó el pie de página adaptable con el nombre del autor y enlace a la página informativa. La página **Acerca de StaySky** está disponible en `/static/acerca.html` e incluye la descripción, el funcionamiento, las funciones, la tecnología y las limitaciones del proyecto.
- Se incorporaron los recursos gráficos `frontend/assets/banner.png` (banner de la página informativa) y `frontend/assets/favicon.png` (icono de pestaña y marca junto al nombre StaySky).

---

## 6. Resultados

### 6.1. Frontend funcional

[INSERTAR CAPTURA: 15_frontend_full.png]
[INSERTAR CAPTURA: 29_acerca_staysky.png]

La aplicación presenta una página principal de planificación y una página informativa:
- **Barra superior fija** con el nombre y el icono de StaySky, un resumen de la última búsqueda y un control para alternar entre tema claro y oscuro, alineado a la derecha; la preferencia visual se guarda en el navegador.
- **Formulario de búsqueda** con origen, destino, fecha de salida, opción de regreso, cantidad de adultos (1–9), presupuesto y preferencia climática (cálido, templado o frío). Los controles comienzan vacíos, incluyen indicaciones y validan la entrada.
- **Viaje recomendado** al inicio de los resultados, con Trip Score de 0 a 100 y resumen de la combinación mejor puntuada.
- **Clima mensual** con 12 tarjetas, temperaturas máximas/mínimas, precipitación, iconos SVG con animaciones sutiles y colores de la paleta. La leyenda marca calor (máxima ≥30 °C), lluvia (promedio ≥1 mm/día), frío (máxima ≤15 °C) y clima moderado; los datos son una estimación histórica de 2023, no un pronóstico diario.
- **Vuelos** ordenados de menor a mayor precio, con solo tres visibles inicialmente y un botón para desplegar el resto. Cada tarjeta muestra logo/nombre de aerolínea, número, horarios, duración, escalas, equipaje, precio y distintivos cuando existen.
- **Alojamientos** con seis opciones destacadas: dos económicas, dos de precio intermedio y dos mejor valoradas. El resto aparece al desplegar la lista. Las tarjetas muestran calificación, estrellas, precio por noche y total.
- **Viaje redondo y grupo:** la fecha de regreso se coloca junto a la fecha de salida; se utiliza para la estancia del hotel y para crear el enlace de vuelo con ambas fechas. Las tarifas mostradas en StaySky son de salida y deben confirmarse en Booking.com. El resumen superior mantiene visibles la ruta, fechas y personas.
- **Paneles de vuelos y alojamientos** alineados en dos columnas en pantallas amplias, y apilados en pantallas pequeñas.
- **Iconografía SVG y colores de marca** índigo (`#4F46E5`), violeta (`#8B5CF6`) y naranja (`#FB923C`), con un gradiente índigo-violeta-naranja, en lugar de depender de emojis.
- **Pie de página adaptable** que se mantiene al final cuando hay poco contenido y aparece después del contenido cuando la página crece; muestra el crédito de Josué Uriel Martínez Ruíz y el enlace a “Acerca de StaySky”.
- **Página “Acerca de StaySky”** servida en `/static/acerca.html`, con el banner `frontend/assets/banner.png`, un resumen del proyecto, su flujo, tecnologías y limitaciones. El favicon `frontend/assets/favicon.png` se utiliza en la pestaña y junto al nombre de la marca.

### 6.2. Documentación OpenAPI automática

[INSERTAR CAPTURA: 03_swagger.png]

FastAPI genera Swagger UI en `/docs` con todos los endpoints tipados, modelos de request/response y el botón "Try it out" para probar sin Postman.

### 6.3. Scoring demostrado

[INSERTAR CAPTURA: 18_score_cun_warm.png]
[INSERTAR CAPTURA: 19_score_cun_cold.png]

La misma ruta (MEX→CUN, 2027-03-12) y presupuesto ($15,000 MXN) producen **85.3** con preferencia cálida y **61.4** con preferencia fría en la consulta realizada para esta revisión. La prueba confirma que el resultado cambia con la preferencia climática. Estos valores dependen de la información cacheada y no son constantes para cualquier búsqueda.

### 6.4. Auditoría del bug USD/MXN

[INSERTAR CAPTURA: 14_currency_audit.png]

En la consulta actual, **15 de 20 hoteles de Cancún (75%)** presentan inconsistencia entre `property.currency` y `priceBreakdown.grossPrice.currency`. StaySky usa la moneda y el importe de `priceBreakdown.grossPrice` como fuente de verdad y conserva la moneda declarada para auditoría.

### 6.5. Airflow orquestando 3 pipelines

[INSERTAR CAPTURA: 22_airflow_dags.png]
[INSERTAR CAPTURA: 24_airflow_logs.png]

Los tres DAGs están configurados para ejecutarse diariamente. En las pruebas de desarrollo se ejecutaron desde Airflow; la API registra las reconstrucciones de estadísticas en `pipeline_runs`. `flights_etl` omite el refresh pago mientras `STAYSKY_CONFIRM_REFRESH` no sea `true`, por lo que su recorrido normal no consume cuota de Booking.

### 6.6. Registro de uso de API

[INSERTAR CAPTURA: 28_usage_still_8.png]

En la revisión del 20 de noviembre de 2026, `/api/flights/usage` reportó **8 respuestas externas exitosas registradas** (7 previas declaradas y 1 registrada por el sistema). La aplicación ya no bloquea al llegar a un límite local de 20: `limit` y `remaining` se devuelven como `null`. RapidAPI conserva sus propias cuotas y puede rechazar solicitudes; el contador local no incluye necesariamente respuestas externas fallidas.

### 6.7. Alcance y limitaciones de la versión

- El catálogo contiene 10 ciudades mexicanas, pero tener una ciudad registrada no significa que haya vuelos u hoteles cacheados para cualquier ruta o fecha.
- En la fotografía del 20 de noviembre de 2026, los vuelos disponibles correspondían a MEX→CUN y MEX→SJD para el 12 de marzo de 2027; los 20 hoteles correspondían a CUN del 12 al 15 de marzo de 2027.
- En la prueba del 22 de noviembre de 2026 se consultó GDL→OAX para el 25 de mayo de 2027, estancia del 25 al 30 de mayo, dos adultos y clima templado. Se guardaron 15 ofertas de vuelo y 20 hoteles; la búsqueda devolvió `tripScore: 83.4`, tres recomendaciones de cada tipo y precios en MXN. La tarifa de vuelo corresponde solo a la salida; el enlace permite consultar el viaje redondo en Booking.com.
- El clima que se muestra es un promedio mensual derivado de datos históricos de 2023. No predice el tiempo de un día futuro.
- El `tripScore` combinado se calcula cuando existen tanto vuelos como hoteles para la búsqueda; si falta alguno, la API puede devolverlo como `null` y explica los datos faltantes en `warnings`.
- La colección `searches` está creada, pero el endpoint de búsqueda no guarda todavía un historial de consultas.
- El proyecto está preparado para desarrollo local y demostración académica. Antes de exponerlo públicamente habría que revisar credenciales, secretos, permisos, límites de API y configuración de despliegue.

### 6.8. Conclusión técnica

El proyecto integra una interfaz web, una API, almacenamiento documental y procesos programados en un entorno reproducible con Docker Compose. Su aporte principal es combinar precio y clima en una recomendación comprensible, sin consultar Booking en cada búsqueda. Las siguientes mejoras naturales serían ampliar las rutas, destinos y fechas cacheadas, guardar el historial de búsquedas y endurecer la configuración antes de cualquier despliegue público.

---

## 7. Reflexión sobre la actividad

> Revisa y personaliza esta reflexión para que describa tu experiencia real y las actividades que realizaste.

Este proyecto me permitió enfrentar por primera vez un escenario donde **las restricciones externas moldean la arquitectura**. Durante el desarrollo, el plan Basic de RapidAPI reportaba 20 requests al mes; esto impulsó decisiones como caché, importación desde JSON, DAGs sin refresh pago por defecto y registro de uso. Para facilitar las pruebas directas se retiró el tope local de StaySky, pero se conservó `confirm=yes`: la cuota, posibles cargos y bloqueos siguen dependiendo de RapidAPI.

Aprendizajes principales:

1. **Contenerizar no es solo "empaquetar".** Docker permitió levantar el entorno completo (6 servicios y 2 bases de datos) en una sola máquina. Con `.env` configurado, `docker compose up --build` reconstruye los servicios; los datos externos deben importarse o actualizarse por separado.

2. **Modelar los datos es tan importante como el código.** Elegir MongoDB para JSON anidados de Booking y PostgreSQL para la metadata de Airflow no fue arbitrario: cada base se usa para lo que hace bien. La lección es que el híbrido no es redundancia, es especialización.

3. **La calidad de los datos es responsabilidad del que integra.** El bug USD/MXN no era un problema de Booking — era mío si lo ignoraba. Detectarlo, cuantificarlo (75% de incidencia), corregirlo y **auditarlo** (guardando `declaredCurrency` y `currencyMismatch` en cada documento) me enseñó que en ingeniería de datos la trazabilidad es tan importante como el fix.

4. **Airflow no es magia, es disciplina.** Escribir DAGs que respeten el contexto (qué ejecutar, cuándo, con qué límites) exige pensar en idempotencia, manejo de errores y desacoplamiento. Aprendí que los pipelines orquestados deben ser re-ejecutables sin efectos secundarios.

5. **El valor está en el scoring, no en la integración.** Conectar tres APIs es trabajo técnico. Diseñar una función que combine sus salidas en un número interpretable para el usuario final — y que ese número demuestre responder a la preferencia declarada (85.3 vs 61.4) — es donde el proyecto genera valor real.

---

## 8. Reflexión sobre el curso y retroalimentación

> Personaliza esta sección de acuerdo con los contenidos y tu experiencia en la materia antes de entregarla.

### Sobre el curso

El curso cumplió el objetivo de introducir las herramientas básicas del área laboral moderna: Docker, contenedores, orquestación y desarrollo web con backend y base de datos. Los temas vistos son directamente aplicables en cualquier empresa que use microservicios o pipelines de datos — es decir, prácticamente cualquier empresa.

### Sugerencias / retroalimentación

1. **Más ejemplos de híbridos de bases de datos.** Durante el proyecto descubrí por mi cuenta que Airflow no soporta MongoDB para su metadata y requiere un SQL adicional. Sería valioso ver en clase ejemplos de "más de una base por sistema" para entender cuándo tiene sentido y cuándo no.

2. **Introducción más temprana a las limitaciones de API de terceros.** Aprender a diseñar con caché obligatorio, contadores de cuota y `import-json` es una habilidad práctica que se subestima. Un mini-ejercicio sobre "cómo consumir una API con plan gratuito" ahorraría muchos dolores de cabeza.

3. **Retroalimentación intermedia por fase.** El plan de siete fases está bien estructurado, pero la validación por hitos ayudaría a no acumular errores hacia el final.

4. **Conexión con casos reales.** Ver proyectos o ejemplos de empresas que resuelven problemas similares (metabuscadores, agregadores de viaje, asistentes de planificación) ayudaría a dimensionar el alcance esperado.

### Qué me llevo

Me llevo la capacidad de **levantar un sistema completo en un solo comando**, de **diagnosticar bugs de calidad de datos** y de **diseñar pipelines orquestados**. Es la primera vez que siento que puedo construir algo que un usuario real podría usar, y eso es exactamente lo que esperaba del curso.

---

## 9. Anexo: uso de IA como apoyo técnico y auditoría

### 9.1. Rol de la IA en el proyecto

Durante el desarrollo se utilizó asistencia de inteligencia artificial como apoyo para consultas técnicas, depuración y organización de la documentación. Esta asistencia no sustituye la revisión del código, las pruebas ni la responsabilidad de comprender y explicar el proyecto.

Antes de entregar, completa esta declaración con las herramientas que realmente utilizaste y de acuerdo con las reglas de la materia. No incluyas servicios o contribuciones que no correspondan a tu experiencia.

### 9.2. Verificación y responsabilidad

Las decisiones finales de diseño, la integración del código y la validación del funcionamiento deben ser revisadas por el responsable del proyecto. Para esta documentación se contrastaron rutas, datos cacheados y resultados de búsqueda contra la API local; las cifras incluidas se identifican como una fotografía de ese entorno y pueden cambiar.

Algunos ejemplos de problemas técnicos documentados son la colisión del nombre `stats` con un método de `mongosh`, el manejo del campo `meta` al importar hoteles y la inicialización de Airflow cuando el usuario administrador ya existe. Las explicaciones de este anexo deben ajustarse a las herramientas y al proceso que efectivamente se siguieron.

### 9.3. Reflexión sobre el uso de IA

El uso de asistentes de IA puede facilitar la exploración de alternativas, la comprensión de errores y la redacción técnica. Sin embargo, sus respuestas pueden contener errores o asumir detalles que no están en el código. Por ello, es importante contrastar las sugerencias con la implementación, ejecutar pruebas y conservar únicamente las afirmaciones que puedan demostrarse.

La transparencia sobre el uso de estas herramientas forma parte de una documentación responsable. El estudiante debe asegurarse de que la declaración final cumpla las políticas de su curso y describa con precisión su propia participación.

---

**Fin del documento.**