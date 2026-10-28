from fastapi import APIRouter, Query
from services.opentripmap import get_pois

router = APIRouter(prefix="/pois", tags=["Points of Interest"])

@router.get("/")
async def points_of_interest(
    lat:      float = Query(..., description="Latitude"),
    lon:      float = Query(..., description="Longitude"),
    theme:    str   = Query("nature", description="heritage|nature|luxury|pilgrimage|beach|adventure|family|budget"),
    radius_m: int   = Query(20000, description="Search radius in metres"),
    limit:    int   = Query(10),
):
    """Fetch points of interest near a location filtered by travel theme."""
    return await get_pois(lat, lon, theme, radius_m, limit)
