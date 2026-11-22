# StaySky

**Planea y compara viajes según tu ruta, presupuesto y clima preferido.**

StaySky es una aplicación web académica que reúne opciones cacheadas de vuelos y hoteles con promedios históricos del clima. La aplicación calcula puntuaciones para ayudar a comparar opciones y enlaza a Booking.com para revisar detalles y disponibilidad.

> **Alcance de los datos:** los vuelos y hoteles aparecen solo cuando existen datos guardados para la ruta y las fechas consultadas. El clima es una referencia histórica, no un pronóstico. Verifica siempre la disponibilidad, las condiciones y el precio final con el proveedor antes de reservar.

## Contenido

- [Funciones](#funciones)
- [Tecnologías y arquitectura](#tecnologías-y-arquitectura)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Requisitos](#requisitos)
- [Configuración y ejecución](#configuración-y-ejecución)
- [Uso de la aplicación](#uso-de-la-aplicación)
- [API](#api)
- [Caché, RapidAPI y llamadas directas](#caché-rapidapi-y-llamadas-directas)
- [MongoDB y datos](#mongodb-y-datos)
- [Airflow](#airflow)
- [Documentación del código](#documentación-del-código)
- [Limitaciones conocidas](#limitaciones-conocidas)
- [Autor](#autor)

## Funciones

- Catálogo inicial de 10 destinos mexicanos.
- Búsqueda por origen, destino, fecha de salida, presupuesto y preferencia de clima.
- Opción de viaje redondo, fecha de regreso y selección de 1 a 9 personas adultas.
- Clima mensual estimado con base en datos históricos de Open-Meteo.
- Vuelos cacheados, ordenados por precio en el listado, con acceso a una búsqueda de reserva en Booking.com.
- Seis hoteles destacados inicialmente: dos económicos, dos de precio intermedio y dos mejor valorados; se puede desplegar el resto.
- Puntuaciones explicables que consideran precio y afinidad climática.
- Temas claro y oscuro, resumen persistente de la búsqueda y diseño adaptable a móvil.
- Página informativa disponible en `/static/acerca.html`, banner e icono de StaySky.
- Importación de respuestas JSON de vuelos y hoteles sin realizar llamadas a RapidAPI.

Los precios de vuelos que muestra StaySky corresponden a la fecha de salida cacheada. En un viaje redondo, el enlace puede incluir la fecha de regreso para consultar la opción completa en Booking.com; StaySky no calcula una tarifa redonda con los datos cacheados.

## Tecnologías y arquitectura

| Componente | Tecnología | Responsabilidad |
|---|---|---|
| Interfaz | HTML5 y Tailwind CSS por CDN | Formulario, resultados y página informativa |
| API | FastAPI, Python 3.11 y Uvicorn | Endpoints, validación y lógica de búsqueda |
| Base de datos del proyecto | MongoDB 7 y Motor | Catálogo, clima, vuelos, hoteles y métricas |
| Base de datos de Airflow | PostgreSQL 15 | Metadata interna del orquestador |
| Procesos programados | Apache Airflow 2.10.3, LocalExecutor | Actualización climática y estadísticas |
| Clima | Open-Meteo Archive | Datos históricos diarios |
| Vuelos y hoteles | Booking.com vía RapidAPI | Fuentes externas para los procesos de refresh |
| Entorno | Docker Compose | Servicios reproducibles en desarrollo |

```text
Navegador
   │ HTML + Tailwind
   ▼
FastAPI ───────────────► Open-Meteo Archive (clima)
   │
   ├── MongoDB (caché, catálogo y métricas)
   └── RapidAPI (solo en endpoints de refresh confirmados)

Airflow ──► FastAPI ──► MongoDB
    └── PostgreSQL almacena la metadata interna de Airflow
```

La búsqueda habitual lee vuelos y hoteles desde MongoDB. Las llamadas externas de Booking están separadas en endpoints de refresh para evitar que cada visita o búsqueda de usuario consuma una solicitud.

## Estructura del proyecto

```text
StaySky/
├── airflow/
│   ├── dags/                  # Pipelines de clima, vuelos y hoteles
│   ├── Dockerfile
│   └── requirements.txt
├── backend/
│   ├── app/
│   │   ├── models/            # Contratos Pydantic de entrada y salida
│   │   ├── routes/            # Endpoints FastAPI por área
│   │   ├── services/          # Clientes externos, normalizadores y scoring
│   │   ├── config.py          # Configuración desde el entorno
│   │   ├── db.py              # Cliente, colecciones e índices de MongoDB
│   │   └── main.py            # Aplicación FastAPI
│   ├── Dockerfile
│   └── requirements.txt
├── docs/
│   ├── api_responses/         # Respuestas JSON guardadas para importación
│   ├── capturas/              # Evidencias visuales
│   └── StaySky_Documentacion.md
├── frontend/
│   ├── assets/                # Banner e icono de marca
│   ├── acerca.html            # Página informativa
│   └── index.html             # Página principal
├── mongo/
│   └── init.js                # Colecciones, índices y ciudades iniciales
├── .env.example
├── docker-compose.yml
└── README.md
```

## Requisitos

- Docker Desktop con Docker Compose.
- Una clave de RapidAPI únicamente si se van a probar los endpoints directos de vuelos u hoteles. Las búsquedas desde caché y la importación JSON no necesitan esa clave.

## Configuración y ejecución

1. Clona o descarga este repositorio y abre una terminal en su carpeta raíz.
2. Crea el archivo local de configuración:

   **PowerShell**
   ```powershell
   Copy-Item .env.example .env
   ```

   **macOS / Linux**
   ```bash
   cp .env.example .env
   ```

3. Si vas a usar RapidAPI, agrega una clave válida en `RAPIDAPI_KEY` dentro de `.env`. No compartas ni subas ese archivo al repositorio.
4. Construye e inicia el stack:

   ```powershell
   docker compose up --build
   ```

5. Abre:

   - Aplicación: <http://localhost:8000>
   - Acerca de StaySky: <http://localhost:8000/static/acerca.html>
   - Swagger UI: <http://localhost:8000/docs>
   - Airflow: <http://localhost:8080>

Detén los servicios con `Ctrl+C` y, si fueron iniciados en segundo plano, ejecuta `docker compose down`. Este comando conserva los datos de los volúmenes.

### Servicios de Compose

Compose define seis servicios: `mongo`, `backend`, `postgres`, `airflow-init`, `airflow-webserver` y `airflow-scheduler`. Las credenciales de Airflow configuradas en Compose (`admin` / `admin`) son solo para desarrollo local; cámbialas antes de exponer el servicio.

## Uso de la aplicación

1. Selecciona origen y destino.
2. Indica fecha de salida; activa **Viaje redondo** si deseas agregar la fecha de regreso.
3. Especifica el número de adultos (1 a 9), presupuesto y clima preferido.
4. Revisa las opciones de vuelos, hoteles, clima histórico y puntuación.
5. Abre Booking.com para confirmar disponibilidad, servicios y precio final.

El formulario valida que los datos requeridos estén completos y que la fecha de regreso sea posterior a la salida. Si no se selecciona regreso, la interfaz usa una estancia predeterminada de tres noches para consultar los hoteles.

## API

La especificación OpenAPI está disponible en `/docs`. Los principales endpoints son:

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/health` | Estado de FastAPI y conexión con MongoDB |
| `GET` | `/api/cities` | Lista el catálogo |
| `GET` | `/api/cities/{iata}` | Consulta una ciudad |
| `POST` | `/api/cities/seed` | Inserta o actualiza las 10 ciudades iniciales |
| `GET` | `/api/weather/{iata}` | Consulta clima histórico, usa caché si hay cobertura |
| `GET` | `/api/weather/{iata}/climate` | Calcula promedios mensuales del clima cacheado |
| `GET` | `/api/flights/{origin}/{destination}?date=YYYY-MM-DD` | Lee vuelos cacheados, ordenados por precio |
| `GET` | `/api/flights/{origin}/{destination}/dates` | Lista fechas de vuelo disponibles en caché |
| `GET` | `/api/flights/usage` | Informa uso de RapidAPI registrado; no bloquea por un límite local |
| `POST` | `/api/flights/usage/seed?used_before=N` | Registra manualmente el uso externo previo para el contador informativo |
| `POST` | `/api/flights/import-json` | Importa ofertas de un JSON sin llamada externa |
| `POST` | `/api/flights/refresh` | Consulta vuelos directamente en RapidAPI; requiere `confirm=yes` |
| `GET` | `/api/hotels/{destination}?checkin=...&checkout=...` | Lee hoteles cacheados |
| `GET` | `/api/hotels/{destination}/dates` | Lista estancias disponibles en caché |
| `GET` | `/api/hotels/{destination}/currency-audit` | Resume discrepancias de moneda registradas |
| `POST` | `/api/hotels/import-json` | Importa hoteles de un JSON sin llamada externa |
| `POST` | `/api/hotels/refresh` | Consulta hoteles directamente en RapidAPI; requiere `confirm=yes` |
| `POST` | `/api/search/` | Combina clima, vuelos, hoteles y puntuaciones |
| `POST` | `/api/admin/rebuild-stats` | Reconstruye estadísticas a partir de MongoDB |
| `GET` | `/api/admin/stats` | Consulta estadísticas agregadas |
| `GET` | `/api/admin/pipeline-runs` | Consulta ejecuciones registradas de pipelines |

### Ejemplo de búsqueda unificada

```json
{
  "origin": "MEX",
  "destination": "CUN",
  "departDate": "2027-03-12",
  "checkout": "2027-03-15",
  "adults": 2,
  "budget": 15000,
  "weatherPref": "warm"
}
```

`checkin` y `checkout` son opcionales en el endpoint de búsqueda. Si se omiten, el backend usa `departDate` como check-in y calcula tres noches. El formulario envía `checkout` cuando se especifica una fecha de regreso.

### Importar vuelos desde un JSON local

Ejemplo para PowerShell desde la raíz del proyecto:

```powershell
curl.exe -X POST "http://localhost:8000/api/flights/import-json?origin=MEX&destination=CUN&date=2027-03-12" `
  -H "Content-Type: application/json" `
  --data-binary "@docs/api_responses/flights_mex_cun.json"
```

Para importar hoteles se usa `POST /api/hotels/import-json` con `destination`, `checkin`, `checkout` y `adults` como parámetros, y el JSON de Booking en el cuerpo.

## Caché, RapidAPI y llamadas directas

- Los endpoints `GET` de vuelos y hoteles consultan MongoDB y no llaman a Booking.
- La importación con `POST .../import-json` procesa un archivo ya obtenido; no consume una solicitud externa.
- Los endpoints `POST .../refresh` son las rutas de llamadas directas y requieren `confirm=yes`.
- **StaySky ya no aplica un tope local de 20 llamadas.** El contador `/api/flights/usage` es informativo y reporta `limit: null` y `remaining: null`.
- **La cuota, bloqueos y posibles cargos del proveedor siguen vigentes.** Quitar el tope de StaySky no aumenta ni modifica los derechos del plan RapidAPI. Verifica tu plan antes de ejecutar refresh; no se realizan llamadas automáticamente al iniciar la aplicación.
- El DAG de vuelos deja el refresh opcional desactivado por defecto (`STAYSKY_CONFIRM_REFRESH=false`). El DAG de hoteles no ejecuta refresh real.

Ejemplo de llamada directa de vuelos en PowerShell (consume el plan externo si RapidAPI la acepta):

```powershell
curl.exe -X POST "http://localhost:8000/api/flights/refresh?origin=MEX&destination=CUN&date=2027-03-12&confirm=yes&adults=1"
```

Para hoteles se requiere una fecha de entrada y salida. El código tiene identificadores de Booking confirmados para Cancún (`CUN`) y Oaxaca (`OAX`); para otro destino hay que proporcionar el identificador:

```powershell
curl.exe -X POST "http://localhost:8000/api/hotels/refresh?destination=CUN&checkin=2027-03-12&checkout=2027-03-15&adults=2&confirm=yes"
```

El contador registra respuestas externas exitosas. Los rechazos del proveedor pueden no aparecer como una llamada completada en el contador local; consulta el panel de RapidAPI para verificar el consumo efectivo.

## MongoDB y datos

La base de datos configurada por defecto es `staysky`. `mongo/init.js` crea las colecciones iniciales e inserta el catálogo de 10 ciudades al inicializar un volumen nuevo.

| Colección | Uso |
|---|---|
| `cities` | Catálogo de ciudades y coordenadas |
| `weather` | Registros climáticos diarios cacheados |
| `flights` | Ofertas de vuelo normalizadas |
| `hotels` | Hoteles normalizados por destino y fechas |
| `searches` | Colección inicial reservada; las búsquedas actuales no se guardan aquí |
| `api_usage` | Respuestas de consultas externas registradas y uso previo declarado |
| `flight_aggregations` | Agregaciones originales de Booking para vuelos |
| `pipeline_stats` | Métricas agregadas de vuelos y hoteles |
| `pipeline_runs` | Historial de reconstrucciones estadísticas |

El normalizador de hoteles toma el importe y moneda de `priceBreakdown.grossPrice` como fuente de verdad y conserva `property.currency` para auditoría, porque la fuente puede reportar ambos campos de manera inconsistente.

Para inspeccionar datos localmente:

```powershell
docker exec -it staysky_mongo mongosh
```

```javascript
use staysky
show collections
db.getCollection("pipeline_stats").countDocuments()
db.getCollection("pipeline_runs").find().sort({timestamp: -1}).limit(5)
```

Se usa `db.getCollection("pipeline_stats")` explícitamente para evitar nombres que pueden coincidir con métodos de `mongosh`.

## Airflow

La interfaz de Airflow está en <http://localhost:8080>. Los DAGs están en `airflow/dags/`:

| DAG | Horario configurado | Función |
|---|---:|---|
| `weather_etl` | Diario 06:00 | Refresca el histórico de las ciudades mediante Open-Meteo |
| `flights_etl` | Diario 07:00 | Reconstruye estadísticas; refresh de vuelos opcional y desactivado por defecto |
| `hotels_etl` | Diario 08:00 | Reconstruye estadísticas y consulta la auditoría de moneda; refresh real deshabilitado |

Los horarios siguen la zona horaria del scheduler de Airflow configurada en el contenedor. PostgreSQL almacena metadata de Airflow; los datos funcionales de StaySky se conservan en MongoDB.

## Documentación del código

El código Python está organizado por responsabilidad y documentado con docstrings:

- `backend/app/main.py`: creación de la aplicación y ciclo de vida de FastAPI.
- `backend/app/config.py` y `backend/app/db.py`: configuración, cliente e índices de MongoDB.
- `backend/app/models/schemas.py`: contratos de request y response.
- `backend/app/routes/`: operaciones HTTP para ciudades, clima, vuelos, hoteles, búsqueda y administración.
- `backend/app/services/`: clientes externos, normalización de respuestas, enlaces y puntuaciones.
- `airflow/dags/`: tareas y dependencias de los procesos programados.

La documentación completa, con decisiones de diseño, resultados y capturas pendientes, está en [`docs/StaySky_Documentacion.md`](docs/StaySky_Documentacion.md).

## Limitaciones conocidas

- Los datos de Booking dependen de la caché y de rutas/fechas que se hayan importado o consultado; el catálogo de ciudades no implica disponibilidad de vuelos u hoteles para todas ellas.
- La información de clima es histórica y no pronostica las condiciones exactas de la fecha de viaje.
- StaySky no realiza reservas ni garantiza precio o disponibilidad.
- La tarifa de vuelo mostrada desde la caché es la de salida incluso si el enlace externo se configura como viaje redondo.
- La búsqueda unificada devuelve resultados cacheados y un score; la colección `searches` no se usa actualmente para guardar historial.
- El stack y credenciales de Compose están preparados para desarrollo local, no para exposición pública sin endurecimiento adicional.

## Autor

**Josué Uriel Martínez Ruíz**

Proyecto académico de planeación de viajes.
