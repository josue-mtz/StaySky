# StaySky - Buscador de Viajes por Clima + Presupuesto
Pipeline de datos en Python que reúne oferta de vuelos, oferta de hoteles y registros climáticos históricos para evaluar destinos y temporadas.

Integra vuelos, hoteles y clima histórico para recomendar destinos.

## Cómo correr

1. Copia `.env.example` a `.env` y pon tu llave de RapidAPI.
2. Ejecuta: `docker compose up --build`
3. Abre: http://localhost:8000
4. Docs API: http://localhost:8000/docs

## Stack
FastAPI · MongoDB · Tailwind (CDN) · Airflow · Docker