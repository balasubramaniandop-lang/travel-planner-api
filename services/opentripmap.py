"""
POI service — curated database for major South India destinations.
Falls back to generic suggestions for unlisted destinations.
Live Overpass API can be enabled later if needed.
"""

# Curated POI database keyed by (lat_rounded, lon_rounded) → theme → list
# Covers Karaikal, Chennai, Coimbatore, Madurai, Trichy, Pondicherry
CURATED_POIS = {
    # Karaikal area (~10.93, ~79.84)
    ("karaikal", "pilgrimage"): [
        {"name": "Karaikal Ammaiyar Temple", "category": "Temple", "hours": "6am–12pm, 4pm–8pm", "entry_fee": "Free", "duration_hrs": 1.0},
        {"name": "Thiruvalangadu Murugan Temple", "category": "Temple", "hours": "6am–12pm, 4pm–8pm", "entry_fee": "Free", "duration_hrs": 1.0},
        {"name": "Punnainallur Mariamman Temple", "category": "Temple", "hours": "6am–1pm, 4pm–9pm", "entry_fee": "Free", "duration_hrs": 1.0},
        {"name": "Keezhaiyur Shiva Temple", "category": "Temple", "hours": "6am–12pm, 5pm–8pm", "entry_fee": "Free", "duration_hrs": 0.5},
        {"name": "Nagapattinam Kayarohana Swami Temple", "category": "Temple (18 km)", "hours": "6am–12pm, 5pm–9pm", "entry_fee": "Free", "duration_hrs": 1.5},
    ],
    ("karaikal", "beach"): [
        {"name": "Karaikal Beach", "category": "Beach", "hours": "All day (morning recommended)", "entry_fee": "Free", "duration_hrs": 2.0},
        {"name": "Akkaraipettai Beach", "category": "Fishing Village Beach", "hours": "All day", "entry_fee": "Free", "duration_hrs": 1.5},
        {"name": "Nagapattinam Beach", "category": "Beach (18 km)", "hours": "All day", "entry_fee": "Free", "duration_hrs": 2.0},
    ],
    ("karaikal", "nature"): [
        {"name": "Pichavaram Mangrove Forest", "category": "Mangrove / Boat Ride (25 km)", "hours": "7am–5pm", "entry_fee": "₹50–₹150 (boat)", "duration_hrs": 3.0},
        {"name": "Point Calimere Wildlife Sanctuary", "category": "Wildlife / Birds (60 km)", "hours": "6am–6pm", "entry_fee": "₹30", "duration_hrs": 4.0},
        {"name": "Velankanni Backwaters", "category": "Nature / Boat (30 km)", "hours": "All day", "entry_fee": "Free", "duration_hrs": 2.0},
    ],
    ("karaikal", "heritage"): [
        {"name": "French War Memorial, Karaikal", "category": "Historic Monument", "hours": "All day", "entry_fee": "Free", "duration_hrs": 0.5},
        {"name": "Nagapattinam Dutch Cemetery", "category": "Historic Site (18 km)", "hours": "All day", "entry_fee": "Free", "duration_hrs": 0.5},
        {"name": "Velankanni Basilica", "category": "Pilgrimage / Heritage (30 km)", "hours": "6am–9pm", "entry_fee": "Free", "duration_hrs": 1.5},
    ],
    # Chennai area
    ("chennai", "heritage"): [
        {"name": "Fort St. George", "category": "Fort / Museum", "hours": "9am–5pm (closed Fri)", "entry_fee": "₹15", "duration_hrs": 2.0},
        {"name": "Government Museum Chennai", "category": "Museum", "hours": "9:30am–5pm (closed Wed)", "entry_fee": "₹15", "duration_hrs": 2.5},
        {"name": "Kapaleeshwarar Temple", "category": "Temple", "hours": "5am–12pm, 4pm–10pm", "entry_fee": "Free", "duration_hrs": 1.0},
    ],
    ("chennai", "beach"): [
        {"name": "Marina Beach", "category": "Beach (2nd longest in world)", "hours": "All day (morning best)", "entry_fee": "Free", "duration_hrs": 2.0},
        {"name": "Elliot's Beach (Besant Nagar)", "category": "Beach", "hours": "All day", "entry_fee": "Free", "duration_hrs": 1.5},
    ],
}

# Lat/lon bounding boxes for city detection
CITY_BOUNDS = [
    ("karaikal", (10.8, 10.97, 79.75, 79.95)),   # lat_min, lat_max, lon_min, lon_max
    ("chennai",  (12.8, 13.25, 79.9, 80.35)),
    ("coimbatore", (10.9, 11.1, 76.85, 77.1)),
    ("madurai",  (9.85, 10.0, 78.0, 78.2)),
    ("trichy",   (10.7, 10.9, 78.6, 78.8)),
    ("pondicherry", (11.85, 12.0, 79.7, 79.9)),
]


def _detect_city(lat: float, lon: float) -> str:
    for city, (lamin, lamax, lomin, lomax) in CITY_BOUNDS:
        if lamin <= lat <= lamax and lomin <= lon <= lomax:
            return city
    return "generic"


def _generic_pois(lat, lon, theme):
    GENERIC = {
        "pilgrimage": ["Nearest Shiva / Vishnu temple complex", "Local Amman temple", "Murugan hilltop shrine"],
        "beach":      ["Nearest coastal viewpoint", "Fishing harbour walk", "Lighthouse beach"],
        "nature":     ["Nearest wildlife sanctuary / bird reserve", "Mangrove forest trail", "Hilltop viewpoint"],
        "heritage":   ["Nearest ASI heritage site", "District museum", "Old fort / palace"],
        "adventure":  ["Trek to nearest hilltop / viewpoint", "River trail / waterfall hike", "Forest dept nature walk"],
        "family":     ["Nearest zoo / children's park", "Water park", "Science centre"],
        "luxury":     ["Nearest 5-star spa resort", "Heritage palace hotel", "Beachfront resort"],
        "budget":     ["Free beach / viewpoint", "Local street food market", "Public park / garden"],
    }
    return [
        {"name": p, "category": theme.title(), "description": "Generic suggestion — verify locally",
         "entry_fee": "Varies", "hours": "Check locally", "duration_hrs": 1.5, "lat": lat, "lon": lon, "source": "generic"}
        for p in GENERIC.get(theme, GENERIC["nature"])
    ]


async def get_pois(lat: float, lon: float, theme: str = "nature",
                   radius_m: int = 20000, limit: int = 10) -> dict:
    city  = _detect_city(lat, lon)
    key   = (city, theme)
    items = CURATED_POIS.get(key)

    if not items:
        # Try theme fallback for detected city
        for t in ["pilgrimage", "nature", "heritage", "beach"]:
            items = CURATED_POIS.get((city, t))
            if items:
                break

    if not items:
        items = _generic_pois(lat, lon, theme)
        note  = "No curated POIs for this location. Showing generic suggestions."
    else:
        note = "Curated POI data for this destination. Verify hours before visiting."

    pois = []
    for p in items[:limit]:
        pois.append({
            "name":         p["name"],
            "category":     p.get("category", theme.title()),
            "description":  p.get("description", ""),
            "entry_fee":    p.get("entry_fee", "Check locally"),
            "hours":        p.get("hours", "Check locally"),
            "duration_hrs": p.get("duration_hrs", 1.5),
            "lat":          p.get("lat", lat),
            "lon":          p.get("lon", lon),
            "source":       "curated",
        })

    return {"lat": lat, "lon": lon, "theme": theme, "pois": pois, "note": note}
