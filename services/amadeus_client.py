"""
Hotel search service using Nuitee Connect API (formerly LiteAPI).
Free tier: No credit card required.
Sign up: https://connect.nuitee.com/register

Nuitee provides 3M+ properties including Indian hotels.
Sandbox/test mode works immediately after signup.
"""
import httpx
import os
from typing import List, Optional

NUITEE_BASE    = "https://api.liteapi.travel"
HOTELS_URL     = f"{NUITEE_BASE}/v3.0/data/hotels"
RATES_URL      = f"{NUITEE_BASE}/v3.0/hotels/rates"

# Rough INR conversion (Nuitee returns USD)
USD_TO_INR = 83.5

# IATA / common code → city name for LiteAPI
CITY_NAMES: dict[str, str] = {
    "MAA": "Chennai",  "BLR": "Bangalore", "BOM": "Mumbai",
    "DEL": "Delhi",    "CCU": "Kolkata",   "HYD": "Hyderabad",
    "COK": "Kochi",    "TRV": "Thiruvananthapuram",
    "IXM": "Madurai",  "TRZ": "Tiruchirappalli",
    "KIK": "Karaikal", "TVR": "Tiruvarur", "NCJ": "Nagapattinam",
    "CBE": "Coimbatore",
}



TIER_STARS = {
    "budget":   "1,2,3",
    "moderate": "3,4",
    "premium":  "4,5",
}


async def search_hotels(
    city_code:   str,
    check_in:    str,
    check_out:   str,
    adults:      int = 2,
    rooms:       int = 1,
    budget_tier: str = "moderate",
) -> dict:
    """
    Search hotels via Nuitee Connect API.
    Falls back to reference estimates when API key not configured.
    Signup (free, no card): https://connect.nuitee.com/register
    """
    api_key = os.getenv("NUITEE_API_KEY", "")
    nights  = (
        __import__("datetime").date.fromisoformat(check_out)
        - __import__("datetime").date.fromisoformat(check_in)
    ).days

    if not api_key:
        # ── Reference fallback (no key) ────────────────────────────────────
        REFERENCE = {
            "budget":   {"range": "₹1,200–₹2,800",  "per_night": 2000},
            "moderate": {"range": "₹3,500–₹7,000",  "per_night": 5000},
            "premium":  {"range": "₹8,000–₹20,000", "per_night": 13000},
        }
        ref = REFERENCE.get(budget_tier, REFERENCE["moderate"])
        pn  = ref["per_night"]
        return {
            "city":      city_code,
            "check_in":  check_in,
            "check_out": check_out,
            "nights":    nights,
            "hotels": [{
                "name":               f"Reference {budget_tier.title()} Hotel",
                "stars":              3 if budget_tier == "moderate" else (2 if budget_tier == "budget" else 5),
                "price_per_night_inr": pn,
                "total_inr":           pn * nights * rooms,
                "cancellation":       "Varies — check property",
                "source":             "reference estimate",
            }],
            "note": (
                f"NUITEE_API_KEY not set. Reference range for {budget_tier}: {ref['range']}/night. "
                "Sign up free (no card) at https://connect.nuitee.com/register — "
                "add key to .env as NUITEE_API_KEY to get live rates."
            ),
        }

    # ── Live Nuitee lookup ─────────────────────────────────────────────────
    headers = {
        "X-API-Key":     api_key,
        "Content-Type":  "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=25, headers=headers) as client:
            # Get hotel list for city
            r1 = await client.get(HOTELS_URL, params={
                "countryCode": "IN", "cityName": CITY_NAMES.get(city_code.upper(), city_code),
                "starRating": TIER_STARS.get(budget_tier, "3,4"),
                "limit":       20,
            })
            r1.raise_for_status()
            raw = r1.json().get("data", [])
            # LiteAPI v3: data is a list of hotel objects
            hotel_data = raw if isinstance(raw, list) else raw.get("hotels", [])
            hotel_ids  = [h.get("hotelId") or h.get("id") for h in hotel_data[:15] if h.get("hotelId") or h.get("id")]

            if not hotel_ids:
                return {
                    "city": city_code, "check_in": check_in, "check_out": check_out,
                    "nights": nights, "hotels": [],
                    "note": "No hotels found in Nuitee for this city/tier.",
                }

            # Get rates
            rates_body = {
                "hotelIds":    hotel_ids,
                "checkin":     check_in,
                "checkout":    check_out,
                "occupancies": [{"adults": adults, "children": []}],
                "currency":    "USD",
                "guestNationality": "IN",
            }
            r2 = await client.post(RATES_URL, json=rates_body)
            r2.raise_for_status()
            rates_data = r2.json().get("data", [])

        # Build name lookup from hotel list
        hotel_name_map = {
            (h.get("hotelId") or h.get("id")): h.get("name", "Unknown Hotel")
            for h in hotel_data
        }

        hotels = []
        for item in rates_data[:8]:
            hotel_id   = item.get("hotelId", "")
            room_types = item.get("roomTypes") or []
            if not room_types:
                continue
            rt   = room_types[0]
            rate = (rt.get("rates") or [{}])[0]

            # Price from rate.retailRate.total
            rr        = rate.get("retailRate", {})
            total_list = rr.get("total", []) if isinstance(rr, dict) else []
            price_usd  = float(total_list[0].get("amount", 0)) if total_list else 0.0

            per_night_inr = round((price_usd / max(nights, 1)) * USD_TO_INR) if price_usd else 0
            total_inr     = round(price_usd * USD_TO_INR) if price_usd else 0

            cancel_info = rate.get("cancellationPolicies", {})
            if isinstance(cancel_info, dict):
                cancel = "Free cancellation" if cancel_info.get("cancelPolicyInfos") else "Non-refundable"
            else:
                cancel = "Check property"

            hotels.append({
                "name":                hotel_name_map.get(hotel_id, hotel_id),
                "hotel_id":            hotel_id,
                "price_per_night_inr": per_night_inr,
                "total_inr":           total_inr,
                "board":               rate.get("boardName") or rate.get("boardType", "RO"),
                "cancellation":        cancel,
                "source":              "LiteAPI (live sandbox)",
            })

        return {
            "city":      city_code,
            "check_in":  check_in,
            "check_out": check_out,
            "nights":    nights,
            "hotels":    sorted(hotels, key=lambda h: h["price_per_night_inr"]),
            "note":      "Live rates from Nuitee Connect. Re-verify on MakeMyTrip before booking.",
        }

    except Exception as exc:
        return {
            "city": city_code, "check_in": check_in, "check_out": check_out,
            "nights": nights, "hotels": [],
            "note": f"Nuitee API error: {exc}. Check your API key or verify on MakeMyTrip.",
        }
