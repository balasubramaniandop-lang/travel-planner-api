"""
Trip cost synthesis + EMI calculator.
Pure Python — no external API required.
"""
from typing import List, Optional
from dataclasses import dataclass, field

# ── Constants ─────────────────────────────────────────────────────────────────
FUEL_PER_KM       = 9.0     # ₹/km petrol SUV avg
TOLL_PER_KM_NH    = 3.0     # ₹/km national highway estimate
GST_BUDGET_MID    = 0.12    # 12% GST on accommodation (budget/moderate)
GST_PREMIUM       = 0.18    # 18% GST on accommodation (luxury)

HOTEL_RATES = {
    "budget":   {"low": 1200, "mid": 2000, "high": 2800},
    "moderate": {"low": 3500, "mid": 5000, "high": 7000},
    "premium":  {"low": 8500, "mid": 13000,"high": 20000},
}

BUFFER_PER_PERSON_DAY = {
    "budget":   800,
    "moderate": 1100,
    "premium":  1800,
}

INSURANCE_PER_PERSON = {
    "budget":   200,
    "moderate": 350,
    "premium":  500,
}

EMI_RATES = {
    3:  0.0,    # No-cost EMI (HDFC/ICICI/SBI partner)
    6:  14.5,
    9:  14.5,
    12: 15.0,
    24: 18.0,
}

EMI_SCHEMES = {
    3:  "No-Cost EMI (HDFC/ICICI/SBI card — partner merchants only)",
    6:  "Standard Credit Card EMI",
    9:  "Standard Credit Card EMI",
    12: "Standard Credit Card EMI",
    24: "Personal Loan / Travel Loan",
}


@dataclass
class CostBand:
    transit_inr:       float = 0.0
    accommodation_inr: float = 0.0
    activities_inr:    float = 0.0
    daily_buffer_inr:  float = 0.0
    insurance_inr:     float = 0.0

    @property
    def total_inr(self) -> float:
        return (
            self.transit_inr
            + self.accommodation_inr
            + self.activities_inr
            + self.daily_buffer_inr
            + self.insurance_inr
        )

    def as_dict(self) -> dict:
        return {
            "transit_inr":       round(self.transit_inr),
            "accommodation_inr": round(self.accommodation_inr),
            "activities_inr":    round(self.activities_inr),
            "daily_buffer_inr":  round(self.daily_buffer_inr),
            "insurance_inr":     round(self.insurance_inr),
            "total_inr":         round(self.total_inr),
        }


def _hotel_cost(tier: str, band: str, nights: int, rooms: int) -> float:
    """Calculate accommodation cost with GST."""
    rate = HOTEL_RATES[tier][band]
    gst  = GST_PREMIUM if tier == "premium" else GST_BUDGET_MID
    return rate * (1 + gst) * nights * rooms


def _transit_cost(
    mode: str,
    distance_km: float,
    train_fare: float,
    flight_fare: float,
    band: str,
    pax: int,
) -> float:
    """Calculate transit cost for a given band."""
    if mode == "drive":
        fuel = distance_km * FUEL_PER_KM
        toll = distance_km * TOLL_PER_KM_NH
        if band == "low":    return fuel * 0.8 + toll * 0.5
        if band == "mid":    return fuel + toll
        return fuel * 1.2 + toll + 1500  # driver stay etc.
    elif mode == "flight":
        if band == "low":    return flight_fare * pax * 0.9
        if band == "mid":    return flight_fare * pax
        return flight_fare * pax * 1.15  # flex fare
    else:  # train / bus
        if band == "low":    return train_fare * pax * 0.8  # Sleeper
        if band == "mid":    return train_fare * pax         # 3AC
        return train_fare * pax * 1.4                        # 2AC


def compute_cost(
    distance_km:    float = 0,
    nights:         int   = 0,
    rooms:          int   = 1,
    adults:         int   = 2,
    children:       int   = 0,
    mode:           str   = "train",
    train_fare_inr: float = 0,
    flight_fare_inr:float = 0,
    activities_inr: float = 0,
    include_insurance: bool = True,
) -> dict:
    """
    Compute 3-band trip cost (budget / moderate / premium).
    All amounts in INR.
    """
    pax = adults + children

    bands = {}
    for tier, band_key in [("budget", "low"), ("moderate", "mid"), ("premium", "high")]:
        transit   = _transit_cost(mode, distance_km, train_fare_inr, flight_fare_inr, band_key, adults)
        hotel     = _hotel_cost(tier, band_key, nights, rooms) if nights > 0 else 0
        buffer    = BUFFER_PER_PERSON_DAY[tier] * pax * max(nights, 1)
        insurance = (INSURANCE_PER_PERSON[tier] * pax) if include_insurance else 0

        bands[tier] = CostBand(
            transit_inr       = transit,
            accommodation_inr = hotel,
            activities_inr    = activities_inr,
            daily_buffer_inr  = buffer,
            insurance_inr     = insurance,
        ).as_dict()

    return bands


def compute_emi(
    principal: float,
    tenures:   Optional[List[int]] = None,
) -> List[dict]:
    """
    Compute EMI options using standard reducing-balance formula.
    EMI = P × r × (1+r)^n / ((1+r)^n – 1)
    For 0% (no-cost EMI), returns simple division.
    """
    if tenures is None:
        tenures = [3, 6, 9, 12, 24]

    options = []
    for n in tenures:
        annual_rate = EMI_RATES.get(n, 15.0)
        if annual_rate == 0.0:
            emi          = round(principal / n, 2)
            total        = round(principal, 2)
        else:
            r   = annual_rate / 12 / 100
            emi = round(principal * r * (1 + r)**n / ((1 + r)**n - 1), 2)
            total = round(emi * n, 2)

        options.append({
            "tenure_months":   n,
            "monthly_emi_inr": emi,
            "annual_rate_pct": annual_rate,
            "total_payable_inr": total,
            "scheme":          EMI_SCHEMES.get(n, "Standard EMI"),
        })

    return options
