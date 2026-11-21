"""
DAG: flights_etl
Recomputa estadísticas de vuelos a partir de datos cacheados (0 requests).

Modo refresh: DESACTIVADO por defecto.
  Si STAYSKY_CONFIRM_REFRESH=true, además refresca 1 ruta (consume 1 request).
"""
import os
from datetime import datetime

import httpx
from airflow import DAG
from airflow.operators.python import PythonOperator

BACKEND = "http://backend:8000"
CONFIRM_REFRESH = os.getenv("STAYSKY_CONFIRM_REFRESH", "false").lower() == "true"


def rebuild_flight_stats(**context):
    """Agrega stats desde Mongo. NO llama RapidAPI."""
    with httpx.Client(timeout=60) as client:
        r = client.post(f"{BACKEND}/api/admin/rebuild-stats?scope=flights")
        r.raise_for_status()
        data = r.json()
        print(f"Stats reconstruidas: {data}")
        return data


def optional_refresh_one_route(**context):
    """
    Solo corre si STAYSKY_CONFIRM_REFRESH=true.
    Consume 1 request de RapidAPI. Se deja como código de ejemplo.
    """
    if not CONFIRM_REFRESH:
        print("Saltando refresh: STAYSKY_CONFIRM_REFRESH != true")
        return {"skipped": True}

    with httpx.Client(timeout=60) as client:
        r = client.post(
            f"{BACKEND}/api/flights/refresh",
            params={
                "origin": "MEX",
                "destination": "CUN",
                "date": "2027-03-12",
                "confirm": "yes",
            },
        )
        print(f"Refresh ejecutado: {r.status_code} {r.json()}")
        return r.json()


with DAG(
    dag_id="flights_etl",
    description="Recomputa stats de vuelos y (opcional) refresca 1 ruta",
    start_date=datetime(2026, 1, 1),
    schedule="0 7 * * *",  # diario 7am
    catchup=False,
    tags=["staysky", "flights"],
) as dag:

    t1 = PythonOperator(
        task_id="rebuild_flight_stats",
        python_callable=rebuild_flight_stats,
    )
    t2 = PythonOperator(
        task_id="optional_refresh_one_route",
        python_callable=optional_refresh_one_route,
    )

    t1 >> t2