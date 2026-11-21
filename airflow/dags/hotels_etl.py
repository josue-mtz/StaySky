"""
DAG: hotels_etl
Recomputa estadísticas de hoteles (incluyendo auditoría USD/MXN).
Modo refresh DESACTIVADO por defecto.
"""
import os
from datetime import datetime

import httpx
from airflow import DAG
from airflow.operators.python import PythonOperator

BACKEND = "http://backend:8000"
CONFIRM_REFRESH = os.getenv("STAYSKY_CONFIRM_REFRESH", "false").lower() == "true"


def rebuild_hotel_stats(**context):
    with httpx.Client(timeout=60) as client:
        r = client.post(f"{BACKEND}/api/admin/rebuild-stats?scope=hotels")
        r.raise_for_status()
        data = r.json()
        print(f"Stats hoteles reconstruidas: {data}")
        return data


def audit_currency_mismatches(**context):
    """Consulta la auditoría del bug USD/MXN para el log del DAG."""
    with httpx.Client(timeout=30) as client:
        r = client.get(f"{BACKEND}/api/hotels/CUN/currency-audit")
        r.raise_for_status()
        audit = r.json()
        print(f"Auditoría CUN: {audit['hotels_with_currency_mismatch']}"
              f"/{audit['total_hotels']} hoteles con bug de moneda")
        return audit


def optional_refresh_one_destination(**context):
    if not CONFIRM_REFRESH:
        print("Saltando refresh: STAYSKY_CONFIRM_REFRESH != true")
        return {"skipped": True}
    print("Refresh real deshabilitado en este proyecto (cuota Basic)")
    return {"disabled": True}


with DAG(
    dag_id="hotels_etl",
    description="Recomputa stats de hoteles + auditoría de moneda",
    start_date=datetime(2026, 1, 1),
    schedule="0 8 * * *",  # diario 8am
    catchup=False,
    tags=["staysky", "hotels"],
) as dag:

    t1 = PythonOperator(
        task_id="rebuild_hotel_stats",
        python_callable=rebuild_hotel_stats,
    )
    t2 = PythonOperator(
        task_id="audit_currency_mismatches",
        python_callable=audit_currency_mismatches,
    )
    t3 = PythonOperator(
        task_id="optional_refresh_one_destination",
        python_callable=optional_refresh_one_destination,
    )

    t1 >> t2 >> t3