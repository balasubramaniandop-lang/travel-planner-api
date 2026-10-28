from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from services.cost_engine import compute_cost, compute_emi

router = APIRouter(prefix="/cost", tags=["Cost & EMI"])

class CostRequest(BaseModel):
    distance_km:     float = 0
    nights:          int   = 0
    rooms:           int   = 1
    adults:          int   = 2
    children:        int   = 0
    mode:            str   = "train"     # train | flight | drive | bus
    train_fare_inr:  float = 0
    flight_fare_inr: float = 0
    activities_inr:  float = 0
    include_insurance: bool = True

class EMIRequest(BaseModel):
    principal: float
    tenures: Optional[List[int]] = [3, 6, 9, 12, 24]

@router.post("/breakdown")
async def cost_breakdown(req: CostRequest):
    """Compute 3-band (budget/moderate/premium) trip cost estimate."""
    bands = compute_cost(
        distance_km     = req.distance_km,
        nights          = req.nights,
        rooms           = req.rooms,
        adults          = req.adults,
        children        = req.children,
        mode            = req.mode,
        train_fare_inr  = req.train_fare_inr,
        flight_fare_inr = req.flight_fare_inr,
        activities_inr  = req.activities_inr,
        include_insurance = req.include_insurance,
    )
    return {**bands, "note": "Reference estimates inclusive of GST. Verify before booking."}

@router.post("/emi")
async def emi_options(req: EMIRequest):
    """Compute EMI table for a given principal using reducing-balance formula."""
    return {
        "principal_inr": req.principal,
        "emi_options":   compute_emi(req.principal, req.tenures),
        "note": "0% EMI available on partner HDFC/ICICI/SBI cards. Processing fee + GST may apply."
    }
