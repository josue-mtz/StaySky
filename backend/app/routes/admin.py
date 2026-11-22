"""
Endpoints administrativos usados por los DAGs de Airflow.
TODOS operan sobre datos cacheados. Ninguno consume RapidAPI.
"""
from fastapi import APIRouter, Query

from app.db import db, flights_col, hotels_col, utcnow

router = APIRouter(prefix="/api/admin", tags=["admin"])
stats_col = db["pipeline_stats"]
pipeline_runs_col = db["pipeline_runs"]


@router.post("/rebuild-stats", summary="Recomputa estadísticas (0 requests)")
async def rebuild_stats(scope: str = Query("all", pattern="^(all|flights|hotels)$")):
    """
    Agrega los datos cacheados en vuelos y hoteles y guarda resúmenes
    en la colección `pipeline_stats`. Lo llaman los DAGs periódicamente.
    """
    result: dict = {"scope": scope, "flights": None, "hotels": None, "timestamp": utcnow()}

    if scope in ("all", "flights"):
        pipeline = [
            {"$group": {
                "_id": {"origin": "$origin", "destination": "$destination", "date": "$departDate"},
                "count": {"$sum": 1},
                "minPrice": {"$min": "$price"},
                "maxPrice": {"$max": "$price"},
                "avgPrice": {"$avg": "$price"},
                "minDurationMinutes": {"$min": "$durationMinutes"},
                "airlines": {"$addToSet": "$airline.code"},
                "cheapestAirline": {"$first": "$airline.code"},
            }},
        ]
        rows = await flights_col.aggregate(pipeline).to_list(length=200)
        for s in rows:
            key = f"flight:{s['_id']['origin']}-{s['_id']['destination']}-{s['_id']['date']}"
            await stats_col.update_one(
                {"key": key},
                {"$set": {"key": key, "type": "flight", **s, "updatedAt": utcnow()}},
                upsert=True,
            )
        result["flights"] = {"routes": len(rows)}

    if scope in ("all", "hotels"):
        pipeline = [
            {"$group": {
                "_id": {
                    "destination": "$destination",
                    "checkin": "$checkinDate",
                    "checkout": "$checkoutDate",
                },
                "count": {"$sum": 1},
                "minPrice": {"$min": "$price"},
                "maxPrice": {"$max": "$price"},
                "avgPrice": {"$avg": "$price"},
                "minRating": {"$min": "$reviewScore"},
                "maxRating": {"$max": "$reviewScore"},
                "currencyMismatches": {
                    "$sum": {"$cond": [{"$eq": ["$currencyMismatch", True]}, 1, 0]}
                },
            }},
        ]
        rows = await hotels_col.aggregate(pipeline).to_list(length=200)
        for s in rows:
            key = f"hotel:{s['_id']['destination']}-{s['_id']['checkin']}-{s['_id']['checkout']}"
            await stats_col.update_one(
                {"key": key},
                {"$set": {"key": key, "type": "hotel", **s, "updatedAt": utcnow()}},
                upsert=True,
            )
        result["hotels"] = {"destinations": len(rows)}

    await pipeline_runs_col.insert_one({"pipeline": "rebuild_stats", **result})
    return result


@router.get("/stats", summary="Ver resúmenes computados")
async def list_stats(type: str | None = Query(None, pattern="^(flight|hotel)$")):
    """Lista las estadísticas agregadas, opcionalmente filtradas por tipo."""
    query = {"type": type} if type else {}
    cursor = stats_col.find(query, {"_id": 0, "updatedAt": 0}).sort("key", 1)
    return await cursor.to_list(length=200)


@router.get("/pipeline-runs", summary="Historial de ejecuciones (auditoría)")
async def pipeline_runs(limit: int = Query(20, ge=1, le=100)):
    """Devuelve las ejecuciones recientes registradas por los pipelines."""
    cursor = pipeline_runs_col.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
    return await cursor.to_list(length=limit)