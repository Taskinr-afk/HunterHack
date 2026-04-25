# backend/app/main.py
from fastapi import FastAPI, Request, Depends, HTTPException
from app.database import init_db, get_potholes, get_pothole_by_id, save_alert, get_alert_history
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.schemas import PotholeFilterParams, AlertRequest, PotholeDetailResponse
from app.auth import verify_admin_key
import os
import re
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# --- Rate Limiter Setup ---
limiter = Limiter(key_func=get_remote_address)

# --- App Init ---
app = FastAPI(title="PotholeTracker NYC", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS Middleware ---
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,   # Only YOUR frontend
    allow_credentials=True,
    allow_methods=["GET", "POST"],   # Only what we actually use
    allow_headers=["*"],
)

# --- Security Headers Middleware ---
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://api.mapbox.com; "
            "img-src 'self' data: https://*.tile.openstreetmap.org https://api.mapbox.com; "
            "connect-src 'self' https://api.mapbox.com https://data.cityofnewyork.us"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)

# --- HTTPS in production only ---
if os.getenv("ENVIRONMENT") == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

# --- Health check route (test that server is running) ---
@app.get("/")
@limiter.limit("100/minute")
async def root(request: Request):
    return {"status": "PotholeTracker API is running"}

# --- Get all potholes (with filtering, rate limited) ---
@app.get("/api/potholes")
@limiter.limit("100/minute")
async def list_potholes(
    request: Request,
    borough: str = None,
    status: str = None,
    limit: int = 100,
    offset: int = 0
):
    # Validate inputs
    params = PotholeFilterParams(borough=borough, status=status, limit=limit, offset=offset)
    potholes = get_potholes(
        borough=params.borough,
        status=params.status,
        limit=params.limit,
        offset=params.offset
    )
    return {"potholes": potholes, "count": len(potholes)}

# --- Get single pothole by ID ---
@app.get("/api/potholes/{pothole_id}", response_model=PotholeDetailResponse)
@limiter.limit("100/minute")
async def get_pothole(request: Request, pothole_id: str):
    # Validate pothole_id format
    if not re.match(r"^[a-zA-Z0-9\-]+$", pothole_id):
        raise HTTPException(status_code=400, detail="Invalid pothole ID format")
    pothole = get_pothole_by_id(pothole_id)
    if not pothole:
        raise HTTPException(status_code=404, detail="Pothole not found")
    return pothole

# --- Send alert (protected by API key) ---
@app.post("/api/alerts/send")
@limiter.limit("10/minute")  # Stricter rate limit for alerts
async def send_alert(
    request: Request,
    alert: AlertRequest,
    authorized: bool = Depends(verify_admin_key)
):
    save_alert(pothole_id=alert.pothole_id, message=alert.message)
    return {"status": "alert_sent", "pothole_id": alert.pothole_id}

# --- Get alert history (protected by API key) ---
@app.get("/api/alerts/history")
@limiter.limit("30/minute")
async def list_alerts(request: Request, authorized: bool = Depends(verify_admin_key)):
    alerts = get_alert_history()
    return {"alerts": alerts, "count": len(alerts)}

# --- Initialize database on startup ---
@app.on_event("startup")
async def startup_event():
    init_db()