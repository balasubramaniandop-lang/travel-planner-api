"""
Train schedule service.
Primary: erail.in AJAX data endpoint (no key required).
Fallback: curated reference timetable for common TN/Kerala routes.
"""
import re
import httpx
from typing import List, Optional

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://erail.in/",
    "X-Requested-With": "XMLHttpRequest",
}

# erail.in AJAX endpoint for trains between stations
ERAIL_DATA_URL = "https://erail.in/data/trains/"

# ---------------------------------------------------------------------------
# Reference timetable – common South India routes (CBE hub)
# Add more as needed
# ---------------------------------------------------------------------------
REFERENCE_TRAINS: dict[tuple, list] = {
    ("CBE", "KIK"): [
        {"number": "16861", "name": "Uzhavan Express", "departure": "06:25", "arrival": "12:45", "duration": "6h 20m", "days": ["Daily"], "classes": ["SL","2A","3A"]},
        {"number": "16863", "name": "Mannai Express", "departure": "22:55", "arrival": "05:10", "duration": "6h 15m", "days": ["Daily"], "classes": ["SL","2A","3A"]},
    ],
    ("CBE", "TPJ"): [
        {"number": "12671", "name": "Nilgiri SF Express", "departure": "10:30", "arrival": "14:30", "duration": "4h 0m", "days": ["Daily"], "classes": ["CC","2S"]},
        {"number": "16609", "name": "Coimbatore–Rameswaram Exp", "departure": "21:10", "arrival": "01:15", "duration": "4h 5m", "days": ["Daily"], "classes": ["SL","2A","3A"]},
    ],
    ("CBE", "MAS"): [
        {"number": "12243", "name": "Shatabdi Express", "departure": "06:00", "arrival": "11:00", "duration": "5h 0m", "days": ["Daily"], "classes": ["CC","EC"]},
        {"number": "12675", "name": "Kovai Express", "departure": "06:05", "arrival": "11:25", "duration": "5h 20m", "days": ["Daily"], "classes": ["CC","2S"]},
    ],
    ("CBE", "SBC"): [
        {"number": "12677", "name": "Ernakulam–Bangalore Express", "departure": "22:35", "arrival": "06:00", "duration": "7h 25m", "days": ["Daily"], "classes": ["SL","2A","3A"]},
    ],
    ("MAS", "KIK"): [
        {"number": "16859", "name": "MS–Karaikal Express", "departure": "21:00", "arrival": "06:30", "duration": "9h 30m", "days": ["Mon","Wed","Fri"], "classes": ["SL","2A","3A"]},
    ],
}


def _reference_lookup(from_code: str, to_code: str) -> list:
    """Return reference trains if we have them for this pair."""
    key = (from_code.upper(), to_code.upper())
    rev = (to_code.upper(), from_code.upper())
    trains = REFERENCE_TRAINS.get(key, [])
    if not trains:
        # reverse direction — swap dep/arr
        for t in REFERENCE_TRAINS.get(rev, []):
            trains.append({**t, "departure": t["arrival"], "arrival": t["departure"]})
    return trains


async def search_trains(
    from_station: str,
    to_station: str,
    date: Optional[str] = None,
) -> dict:
    from_code = from_station.strip().upper()
    to_code   = to_station.strip().upper()

    trains: List[dict] = []
    source = "reference"

    # --- Try erail.in AJAX endpoint ---
    try:
        params = {
            "Source":      from_code,
            "Destination": to_code,
            "SType":       "S",
            "SearchFor":   "TR",
            "Dist":        "0",
            "StationName": "",
        }
        async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
            resp = await client.get(ERAIL_DATA_URL, params=params)
            if resp.status_code == 200:
                data = resp.json() if resp.headers.get("content-type","").startswith("application/json") else {}
                raw_trains = data.get("Trains") or data.get("trains") or []
                for t in raw_trains:
                    trains.append({
                        "number":    str(t.get("TrainNo") or t.get("number", "")),
                        "name":      str(t.get("TrainName") or t.get("name", "")),
                        "departure": str(t.get("Source_Departure_Time") or t.get("departure", "N/A")),
                        "arrival":   str(t.get("Destination_Arrival_Time") or t.get("arrival", "N/A")),
                        "duration":  str(t.get("Duration") or t.get("duration", "N/A")),
                        "days":      t.get("RunningDays") or t.get("days") or ["Daily"],
                        "classes":   t.get("AvailClasses") or t.get("classes") or ["SL","2A","3A"],
                        "source":    "erail.in",
                    })
                if trains:
                    source = "erail.in (live)"
    except Exception:
        pass  # fall through to reference data

    # --- Fallback to reference timetable ---
    if not trains:
        trains = _reference_lookup(from_code, to_code)
        source = "reference timetable"

    note = f"Source: {source}. Verify availability and book on IRCTC."
    if not trains:
        note = (
            "No direct trains found for this route. "
            "Try via Tiruchchirapalli (TPJ) or Chennai (MAS), or check IRCTC directly."
        )

    return {
        "from_station": from_code,
        "to_station":   to_code,
        "trains":       trains,
        "note":         note,
    }
