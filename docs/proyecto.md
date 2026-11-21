# StaySky
## Buscador inteligente de viajes por clima y presupuesto

**Proyecto Final · Desarrollo de Aplicaciones con Docker**

**Autor:** [Tu nombre completo]
**Matrícula:** [Tu matrícula]
**Materia:** [Nombre de la materia]
**Profesor:** [Nombre del profesor]
**Fecha:** Noviembre 2026

---

## Índice

1. Resumen ejecutivo
2. Problema a solucionar
3. Objetivos del proyecto
4. Herramientas utilizadas
5. Arquitectura de la aplicación
6. Descripción del desarrollo (por fases)
7. Resultados y capturas
8. Asistencia de IA en el proyecto
9. Reflexión sobre la actividad
10. Reflexión sobre el curso y retroalimentación
11. Conclusiones
12. Referencias

---

## 1. Resumen ejecutivo

**StaySky** es una aplicación web que combina tres fuentes de datos —vuelos, hoteles y clima histórico— para recomendar destinos turísticos en México en función de la preferencia climática del usuario y su presupuesto total. El usuario indica origen, destino, fecha, presupuesto y tipo de clima deseado (cálido, templado o frío), y el sistema devuelve un **score de 0 a 100** que combina el ajuste climático con el ajuste presupuestal, junto con el top 3 de vuelos y hoteles ordenados por conveniencia.

El proyecto se construyó con **FastAPI + MongoDB + Airflow + Docker** y se complementa con un frontend en HTML + Tailwind CSS servido directamente por FastAPI. La ingesta de datos se automatiza con tres DAGs de Airflow que mantienen actualizado el catálogo de ciudades, el clima histórico y las estadísticas agregadas.

**Resultados destacados:**
- 10 destinos mexicanos, 30 ofertas de vuelo, 20 hoteles y ~3,650 registros de clima en MongoDB.
- Sistema completo funcionando con **solo 8 de 20 requests** disponibles en la cuota mensual de RapidAPI.
- Detección y corrección automática de un **bug de inconsistencia monetaria (USD vs MXN)** que afectaba al 75% de los hoteles de Cancún.
- Algoritmo de scoring con capacidad de discriminación de **24 puntos** entre preferencias climáticas opuestas (85.3 vs 61.4 para el mismo destino).

---

## 2. Problema a solucionar

Planificar un viaje hoy requiere consultar **tres fuentes distintas y descoordinadas**:

1. Un metabuscador de vuelos (Google Flights, Skyscanner, Booking Flights) para encontrar el vuelo más económico.
2. Un metabuscador de hoteles (Booking, Airbnb, Expedia) para comparar opciones de hospedaje.
3. Un sitio meteorológico (Weather.com, AccuWeather) para verificar el clima esperado en la fecha del viaje.

El usuario debe abrir tres pestañas, comparar manualmente, tomar notas y decidir con base en información dispersa. Además:

- Los buscadores de vuelos **no consideran el clima** al ordenar resultados.
- Los buscadores de hoteles **no filtran por preferencia climática**.
- Los sitios meteorológicos **no integran precios** de vuelos ni hospedaje.
- Los precios y disponibilidades cambian constantemente, lo que dificulta comparaciones hechas "a mano".

En México, además, la estacionalidad climática es muy marcada: Cancún en marzo es soleado y cálido, mientras que Monterrey o Los Cabos pueden estar más frescos. Un usuario que **prefiere el clima frío** y busca "playa" en marzo puede terminar en Cancún a 30°C sin desearlo, porque ninguna herramienta integra su preferencia climática con la oferta real.

**¿Qué falta?** Una herramienta que **unifique** las tres fuentes, aplique un criterio objetivo de recomendación y exponga el resultado como un score claro y accionable.

---

## 3. Objetivos del proyecto

### Objetivo general

Construir una aplicación web funcional, contenerizada con Docker, que integre oferta real de vuelos, oferta hotelera y clima histórico para recomendar destinos turísticos mexicanos en función de la preferencia climática y el presupuesto del usuario.

### Objetivos específicos

1. **Integrar** tres fuentes de datos heterogéneas (Booking.com vía RapidAPI, Open-Meteo Archive API y un catálogo propio de ciudades) mediante servicios Python tipados.
2. **Normalizar** los datos crudos a un esquema documental en MongoDB que permita consultas rápidas y soporte la evolución del proyecto (nacional → internacional).
3. **Automatizar** la ingesta y actualización periódica de datos con **Apache Airflow**, garantizando que el catálogo de vuelos y hoteles esté cacheado y el clima se mantenga actualizado diariamente.
4. **Implementar** un algoritmo de scoring que combine precio y clima de forma transparente y ponderada, documentado y auditable.
5. **Contenerizar** toda la aplicación (backend, base de datos, orquestador y metadata) con `docker-compose`, de forma que un tercero pueda ejecutarla con un solo comando.
6. **Aplicar** reglas de calidad de datos que detecten y corrijan inconsistencias reales de las APIs (por ejemplo, el campo `currency` de Booking Hotels vs la moneda real de `priceBreakdown`).
7. **Optimizar** el consumo de una API de pago con cuota limitada (20 requests/mes) mediante estrategias de caché, importación offline de JSON y DAGs que no consumen cuota.

---

## 4. Herramientas utilizadas

| Categoría | Herramienta | Versión | Propósito |
|---|---|---|---|
| Lenguaje | Python | 3.11 | Backend y DAGs |
| Framework web | FastAPI | 0.115 | API REST async con Swagger auto-generado |
| Servidor ASGI | Uvicorn | 0.32 | Servidor de desarrollo con hot-reload |
| Base de datos principal | MongoDB | 7.0 | Documentos JSON para datos anidados |
| Driver asíncrono Mongo | Motor | 3.6 | Cliente async oficial |
| Base de datos de orquestación | PostgreSQL | 15 | Solo metadata interna de Airflow |
| Orquestador | Apache Airflow | 2.10.3 | DAGs de ingesta y recomputo |
| Ejecutor Airflow | LocalExecutor | (incluido) | Ejecución paralela de tasks |
| Contenedores | Docker + Compose | 27.x | Aislamiento y orquestación local |
| Frontend | HTML + Tailwind CSS | CDN | UI sin build step |
| Clima | Open-Meteo Archive API | v1 | Histórico diario gratuito |
| Vuelos y hoteles | Booking.com vía RapidAPI | Plan Basic | Fuente principal de oferta |
| Validación de datos | Pydantic | 2.9 | Schemas y validación de entrada/salida |
| Cliente HTTP | HTTPX | 0.27 | Llamadas async a APIs externas |
| Configuración | pydantic-settings + python-dotenv | 2.6 / 1.0 | Lectura de `.env` |

**Restricciones técnicas relevantes:**

- **Cuota RapidAPI:** plan Basic de **20 requests/mes** (límite duro). Esto condicionó **todas** las decisiones de arquitectura: caché obligatorio, importación offline de JSON preexistente, DAGs que no llaman API externa en producción.
- **Open-Meteo Archive:** entrega datos históricos (no pronósticos futuros a 2027). Se usó como **proxy estacional**: el clima de marzo 2023 se toma como referencia de "cómo es marzo" en cada destino.
- **Airflow no soporta MongoDB** para su metadata interna (solo motores SQL vía SQLAlchemy). De ahí el **híbrido MongoDB + PostgreSQL**.

---

## 5. Arquitectura de la aplicación

### 5.1. Vista de componentes
