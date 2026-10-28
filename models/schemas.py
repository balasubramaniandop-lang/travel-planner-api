"""
Pydantic schemas for Travel Planner API request/response models.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class TravelMode(str, Enum):
    TRAIN = "train"
    FLIGHT = "flight"
    DRIVE = "drive"
    BUS = "bus"
    AUTO = "auto"


class TripTheme(str, Enum):
    HERITAGE = "heritage"
    NATURE = "nature"
    LUXURY = "luxury"
    BUDGET = "budget"
    PILGRIMAGE = "pilgrimage"
    BEACH = "beach"
    ADVENTURE = "adventure"
    FAMILY = "family"


# ── Train Search ──────────────────────────────────────────────────────────────
class TrainSearchRequest(BaseModel):
    from_station: str = Field(..., description="Station name or code, e.g. 'CBE' or 'Coimbatore'")
    to_station: str = Field(..., description="Station name or code, e.g. 'NMJ' or 'Nidamangalam'")
    date: Optional[str] = Field(None, description="Travel date YYYY-MM-DD; omit for any day")

class TrainInfo(BaseModel):
    number: str
    name: str
    departure: str
    arrival: str
    duration: str
    days: List[str]
    classes: List[str]
    source: str = "erail.in"

class TrainSearchResponse(BaseModel):
    from_station: str
    to_station: str
    trains: List[TrainInfo]
    note: str = "Verify availability and book on IRCTC before travel."


# ── Weather ───────────────────────────────────────────────────────────────────
class WeatherRequest(BaseModel):
    destination: str
    date: str = Field(..., description="Date YYYY-MM-DD")
    lat: Optional[float] = None
    lon: Optional[float] = None

class WeatherResponse(BaseModel):
    destination: str
    date: str
    mode: str   # "forecast" or "historical_climate"
    temp_high_c: float
    temp_low_c: float
    rain_probability_pct: int
    condition: str
    advisory: str
    packing_tips: List[str]


# ── Hotel Search ──────────────────────────────────────────────────────────────
class HotelSearchRequest(BaseModel):
    city_code: str = Field(..., description="IATA city code, e.g. 'MAA' for Chennai")
    check_in: str = Field(..., description="YYYY-MM-DD")
    check_out: str = Field(..., description="YYYY-MM-DD")
    adults: int = 2
    rooms: int = 1
    budget_tier: Optional[str] = Field("moderate", description="budget | moderate | premium")

class HotelOffer(BaseModel):
    name: str
    stars: int
    price_per_night_inr: float
    total_inr: float
    cancellation: str
    source: str

class HotelSearchResponse(BaseModel):
    city: str
    check_in: str
    check_out: str
    nights: int
    hotels: List[HotelOffer]
    note: str = "Reference rate — verify on MakeMyTrip/Goibibo before booking."


# ── Cost Synthesis ────────────────────────────────────────────────────────────
class CostRequest(BaseModel):
    distance_km: float = 0
    nights: int = 0
    rooms: int = 1
    hotel_tier: str = "moderate"
    adults: int = 2
    children: int = 0
    mode: TravelMode = TravelMode.TRAIN
    train_fare_inr: float = 0
    flight_fare_inr: float = 0
    activities_inr: float = 0
    include_insurance: bool = True
    emi_principal: Optional[float] = None
    emi_tenures: Optional[List[int]] = [3, 6, 9, 12, 24]

class EMIOption(BaseModel):
    tenure_months: int
    monthly_emi_inr: float
    annual_rate_pct: float
    total_payable_inr: float
    scheme: str

class CostBand(BaseModel):
    transit_inr: float
    accommodation_inr: float
    activities_inr: float
    daily_buffer_inr: float
    insurance_inr: float
    total_inr: float

class CostResponse(BaseModel):
    budget: CostBand
    moderate: CostBand
    premium: CostBand
    emi_options: Optional[List[EMIOption]] = None
    note: str = "All figures are reference estimates inclusive of GST. Verify before booking."


# ── Trip Plan (unified) ───────────────────────────────────────────────────────
class TripPlanRequest(BaseModel):
    origin: str
    destination: str
    waypoints: Optional[List[str]] = []
    check_in: str
    check_out: str
    adults: int = 1
    children: int = 0
    budget_inr: Optional[float] = None
    theme: TripTheme = TripTheme.NATURE
    mode: TravelMode = TravelMode.AUTO
