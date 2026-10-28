from fastapi import APIRouter, Query
from typing import Optional
from services.erail_scraper import search_trains

router = APIRouter(prefix="/trains", tags=["Trains"])

@router.get("/search")
async def train_search(
    from_station: str = Query(..., description="Station code or name (e.g. CBE)"),
    to_station:   str = Query(..., description="Station code or name (e.g. NMJ)"),
    date: Optional[str] = Query(None, description="Travel date YYYY-MM-DD"),
):
    """Search direct trains between two stations via erail.in."""
    return await search_trains(from_station, to_station, date)
