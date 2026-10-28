"""
Weather service using Open-Meteo (free, no API key required).
- Forecast mode:  trip ≤ 14 days away  → 7-day forecast API
- Historical mode: trip > 14 days away → climatology API (30-year averages)
"""
import httpx
from datetime import date, datetime, timedelta
from typing import Optional

# Geocoding for destination → lat/lon (Open-Meteo geocoding API — also free)
GEO_URL      = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
CLIMATE_URL  = "https://climate-api.open-meteo.com/v1/climate"

CONDITION_MAP = {
    range(0,  1):  "Clear sky",
    range(1,  4):  "Mainly clear",
    range(45, 49): "Foggy",
    range(51, 58): "Drizzle",
    range(61, 68): "Rain",
    range(71, 78): "Snow",
    range(80, 83): "Rain showers",
    range(95, 100):"Thunderstorm",
}

PACKING_RULES = {
    "rain":        "☐ Rain poncho / compact umbrella",
    "hot":         "☐ Sunscreen SPF 50+ | ☐ Light cotton clothes | ☐ Hat / cap",
    "cool":        "☐ Light woolens / fleece jacket",
    "coastal":     "☐ Sunscreen | ☐ Flip-flops | ☐ Waterproof bag for electronics",
    "general":     "☐ Power bank | ☐ Motion sickness tablets | ☐ Insect repellent",
}

MONSOON_ADVISORY = (
    "⚠ NE Monsoon season (Oct–Dec) for coastal SE India. Expect intermittent heavy rain. "
    "Carry rain gear; outdoor activities best scheduled before noon. "
    "Check NDRF alerts for cyclone watches."
)


async def _geocode(destination: str) -> tuple[float, float]:
    """Return (lat, lon) for a destination name."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(GEO_URL, params={"name": destination, "count": 1, "language": "en"})
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results:
            raise ValueError(f"Cannot geocode destination: {destination}")
        return results[0]["latitude"], results[0]["longitude"]


def _wmo_condition(code: int) -> str:
    for r, label in CONDITION_MAP.items():
        if code in r:
            return label
    return "Variable"


async def get_weather(
    destination: str,
    travel_date: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> dict:
    """
    Returns weather profile for a destination on a given date.
    Uses forecast for dates ≤ 14 days out; historical climate otherwise.
    """
    trip_dt   = datetime.strptime(travel_date, "%Y-%m-%d").date()
    today     = date.today()
    days_away = (trip_dt - today).days

    # Geocode if lat/lon not provided
    if lat is None or lon is None:
        try:
            lat, lon = await _geocode(destination)
        except Exception:
            # Rough defaults for common Tamil Nadu destinations
            DEFAULTS = {
                "karaikal":      (10.93, 79.84),
                "nidamangalam":  (10.82, 79.44),
                "coimbatore":    (11.00, 76.97),
                "tiruvarur":     (10.77, 79.63),
                "ooty":          (11.41, 76.70),
                "chennai":       (13.08, 80.27),
                "madurai":       (9.93,  78.12),
            }
            key = destination.lower()
            lat, lon = next(
                (v for k, v in DEFAULTS.items() if k in key),
                (11.00, 78.00)   # Tamil Nadu center fallback
            )

    # ── Forecast mode (≤ 14 days) ─────────────────────────────────────────────
    if 0 <= days_away <= 14:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(FORECAST_URL, params={
                    "latitude":   lat,
                    "longitude":  lon,
                    "daily":      "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
                    "timezone":   "Asia/Kolkata",
                    "start_date": travel_date,
                    "end_date":   travel_date,
                })
                r.raise_for_status()
                daily = r.json().get("daily", {})

            temp_high = daily["temperature_2m_max"][0]
            temp_low  = daily["temperature_2m_min"][0]
            rain_prob = daily["precipitation_probability_max"][0]
            wmo_code  = daily["weathercode"][0]
            condition = _wmo_condition(wmo_code)
            mode      = "7-day forecast"
        except Exception:
            # Fall through to climate estimate
            days_away = 15

    # ── Historical climate mode (> 14 days) ───────────────────────────────────
    if days_away > 14:
        try:
            # Climate API uses month averages; use same month of previous year
            ref_start = trip_dt.replace(year=trip_dt.year - 1, day=1)
            import calendar
            last_day  = calendar.monthrange(ref_start.year, ref_start.month)[1]
            ref_end   = ref_start.replace(day=last_day)

            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(CLIMATE_URL, params={
                    "latitude":  lat,
                    "longitude": lon,
                    "start_date": str(ref_start),
                    "end_date":   str(ref_end),
                    "models":    "EC_Earth3P_HR",
                    "daily":     "temperature_2m_max,temperature_2m_min,precipitation_sum",
                })
                r.raise_for_status()
                daily = r.json().get("daily", {})

            temps_high = [t for t in daily.get("temperature_2m_max", []) if t is not None]
            temps_low  = [t for t in daily.get("temperature_2m_min", []) if t is not None]
            precip     = [p for p in daily.get("precipitation_sum",  []) if p is not None]

            temp_high  = round(sum(temps_high) / len(temps_high), 1) if temps_high else 32.0
            temp_low   = round(sum(temps_low)  / len(temps_low),  1) if temps_low  else 24.0
            rainy_days = sum(1 for p in precip if p > 1.0)
            rain_prob  = round(rainy_days / len(precip) * 100) if precip else 40
            condition  = "Historical monthly average"
            mode       = "30-year climate average"
        except Exception:
            temp_high, temp_low, rain_prob, condition = 33.0, 25.0, 50, "Estimate (API unavailable)"
            mode = "estimate"

    # ── Advisory ──────────────────────────────────────────────────────────────
    month = trip_dt.month
    advisory_parts = []

    # NE Monsoon coastal SE India
    if month in (10, 11, 12) and lon > 79.0:
        advisory_parts.append(MONSOON_ADVISORY)
    if rain_prob > 60:
        advisory_parts.append(
            "Rain likely. Schedule outdoor activities in the morning; have indoor fallbacks for afternoon."
        )
    if temp_high > 35:
        advisory_parts.append(
            "Hot day expected. Outdoor activities only 7–10 AM and 4–6 PM; midday = AC venues."
        )
    if not advisory_parts:
        advisory_parts.append("Conditions look manageable. Carry a light jacket for evenings.")

    # ── Packing tips ──────────────────────────────────────────────────────────
    tips = []
    if rain_prob > 40:
        tips.append(PACKING_RULES["rain"])
    if temp_high > 33:
        tips.append(PACKING_RULES["hot"])
    if temp_low < 22:
        tips.append(PACKING_RULES["cool"])
    if lon > 79.5:   # coastal
        tips.append(PACKING_RULES["coastal"])
    tips.append(PACKING_RULES["general"])

    return {
        "destination":          destination,
        "date":                 travel_date,
        "mode":                 mode,
        "temp_high_c":          temp_high,
        "temp_low_c":           temp_low,
        "rain_probability_pct": rain_prob,
        "condition":            condition,
        "advisory":             " ".join(advisory_parts),
        "packing_tips":         tips,
    }
