"""
Travel Planner API — FastAPI backend
Phase 2: Live data integrations (trains, weather, hotels, POIs, cost/EMI)

Run locally:
    cd backend
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

Swagger UI: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()   # load .env file from backend/ directory

from routes import trains, weather, hotels, cost, pois

app = FastAPI(
    title       = "Travel Planner API",
    description = (
        "AI-powered travel planning backend for Indian travelers. "
        "Live train schedules (erail.in), weather (Open-Meteo), "
        "hotel rates (Amadeus), POIs (OpenTripMap), cost synthesis & EMI."
    ),
    version = "2.0.0",
    docs_url= "/docs",
)

# ── CORS (allow Claude skill and any local frontend) ──────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(trains.router)
app.include_router(weather.router)
app.include_router(hotels.router)
app.include_router(cost.router)
app.include_router(pois.router)

# ── Health / root ─────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {
        "status":  "ok",
        "service": "Travel Planner API v2",
        "docs":    "/docs",
        "apis_configured": {
            "amadeus":      bool(os.getenv("AMADEUS_CLIENT_ID")),
            "opentripmap":  bool(os.getenv("OPENTRIPMAP_API_KEY")),
            "open_meteo":   True,   # No key required
            "erail_scraper":True,   # No key required
        }
    }

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}
