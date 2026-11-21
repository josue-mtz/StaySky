"""
DAG: weather_etl
Refresca el clima histórico de las 10 ciudades desde Open-Meteo.
Open-Meteo es gratis, así que puede correr diariamente sin costo.
"""
from datetime import datetime, timedelta

import httpx
from airflow import DAG
from airflow.operators.python import PythonOperator

BACKEND = "http://backend:8000"
START_DATE = "2023-01-01"
END_DATE = "2023-12-31"


def refresh_all_cities_weather(**context):
    """Itera las 10 ciudades y refresca el clima cacheado."""
    with httpx.Client(timeout=120) as client:
        cities = client.get(f"{BACKEND}/api/cities").json()
        results = []

        for city in cities:
            try:
                r = client.get(
                    f"{BACKEND}/api/weather/{city['iata']}",
                    params={
                        "start_date": START_DATE,
                        "end_date": END_DATE,
                        "refresh": True,
                    },
                )
                data = r.json()
                results.append({
                    "iata": city["iata"],
                    "status": r.status_code,
                    "days": data.get("count", 0),
                })
            except Exception as exc:
                results.append({"iata": city["iata"], "error": str(exc)})

        print(f"Refrescadas {len(results)} ciudades:")
        for r in results:
            print(f"  {r}")

        # Guardar log en Mongo vía backend (opcional pero auditable)
        context["ti"].xcom_push(key="results", value=results)
        return results


with DAG(
    dag_id="weather_etl",
    description="Refresca clima histórico de 10 ciudades cada día",
    start_date=datetime(2026, 1, 1),
    schedule="0 6 * * *",  # todos los días a las 6am
    catchup=False,
    tags=["staysky", "weather"],
) as dag:

    refresh_task = PythonOperator(
        task_id="refresh_all_cities_weather",
        python_callable=refresh_all_cities_weather,
    )