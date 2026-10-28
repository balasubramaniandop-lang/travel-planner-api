from fastapi import APIRouter, Query
from services.amadeus_client import search_hotels

router = APIRouter(prefix="/hotels", tags=["Hotels"])

@router.get("/search")
async def hotel_search(
    city_code:   str = Query(..., description="IATA city code e.g. MAA"),
    check_in:    str = Query(..., description="YYYY-MM-DD"),
    check_out:   str = Query(..., description="YYYY-MM-DD"),
    adults:      int = Query(2),
    rooms:       int = Query(1),
    budget_tier: str = Query("moderate", description="budget | moderate | premium"),
):
    """Search hotel availability and rates via Amadeus API."""
    return await search_hotels(city_code, check_in, check_out, adults, rooms, budget_tier)
