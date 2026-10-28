from fastapi import APIRouter, Query
from typing import Optional
from services.weather import get_weather

router = APIRouter(prefix="/weather", tags=["Weather"])

@router.get("/")
async def weather(
    destination: str = Query(..., description="Destination city name"),
    date: str        = Query(..., description="Travel date YYYY-MM-DD"),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
):
    """Get weather forecast or historical climate profile for a destination."""
    return await get_weather(destination, date, lat, lon)
