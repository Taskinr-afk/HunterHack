# Backend & ML Plan — PotholeTracker NYC

> **Audience:** Beginners who just started coding. Every step is explicit with commands to run, files to create, and code to write.

---

## Phase 0: Python Environment Setup

### Step 0.1: Install Python
**What:** Python runs our backend and ML code.

**How:**
1. Go to https://www.python.org/downloads/
2. Download Python 3.11+ (3.11 or 3.12 recommended)
3. **Important:** Check "Add Python to PATH" during installation on Windows
4. Verify:
```bash
python --version    # Should show 3.11.x or 3.12.x
pip --version       # Should show pip 24.x
```

**If `python` doesn't work on Windows:** Try `py` instead, or restart your terminal.

---

### Step 0.2: Create a virtual environment
**What:** A virtual environment keeps this project's Python packages separate from your system Python.

```bash
cd ~/HunterHack
mkdir -p backend
cd backend

# Create virtual environment
python -m venv venv

# Activate it (Windows with bash):
source venv/Scripts/activate

# Verify you're in the venv:
which python  # Should show .../backend/venv/bin/python or .../Scripts/python
```

**Every time you open a new terminal**, you need to activate the venv:
```bash
cd ~/HunterHack/backend
source venv/Scripts/activate
```

You'll know it's active when your terminal prompt shows `(venv)`.

---

### Step 0.3: Install all Python dependencies at once
**Create `backend/requirements.txt`:**
```
fastapi==0.115.0
uvicorn==0.30.0
httpx==0.27.0
pandas==2.2.3
numpy==2.1.0
scikit-learn==1.5.2
xgboost==2.1.1
joblib==1.4.2
python-dotenv==1.0.1
slowapi==0.5.1
pydantic==2.9.0
```

**Install:**
```bash
cd ~/HunterHack/backend
source venv/Scripts/activate
pip install -r requirements.txt
```

**Verify:**
```bash
python -c "import fastapi; print(fastapi.__version__)"  # Should print 0.115.0
python -c "import xgboost; print(xgboost.__version__)"  # Should print 2.1.1
```

---

### Step 0.4: Create project folder structure
```bash
cd ~/HunterHack/backend
mkdir -p app/{api,models,services,schemas}
mkdir -p data/{raw,processed}
mkdir -p ml
```

Your structure:
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py            ← FastAPI app entry point
│   ├── database.py        ← SQLite connection + schema
│   ├── api/
│   │   ├── __init__.py
│   │   ├── potholes.py    ← /api/potholes endpoints
│   │   ├── stats.py       ← /api/stats endpoints
│   │   ├── predictions.py ← /api/predictions endpoints
│   │   └── alerts.py      ← /api/alerts endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   └── ml_models.py  ← ML model loading & prediction
│   ├── services/
│   │   ├── __init__.py
│   │   ├── etl.py          ← Data fetching & processing
│   │   ├── geospatial.py  ← Distance calculations
│   │   └── alert_service.py ← Alert generation
│   └── schemas.py         ← Pydantic request/response models
├── ml/
│   ├── train_accident_risk.py  ← Train accident risk model
│   ├── train_repair_time.py    ← Train repair timeline model
│   └── feature_engineering.py ← Feature creation
├── data/
│   ├── raw/                ← Downloaded CSV data
│   └── processed/          ← Cleaned/joined data
├── venv/                   ← Virtual environment (gitignored)
├── requirements.txt
└── .env                    ← Secrets (gitignored)
```

---

## Phase 1: Database Setup

### Step 1.1: Create the database module
**What:** SQLite database with all the tables our app needs.

**Create `backend/app/database.py`:**
```python
import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./potholes.db").replace("sqlite:///", "")

def init_db():
    """Create all tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS potholes (
                id TEXT PRIMARY KEY,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                borough TEXT,
                zip_code TEXT,
                descriptor TEXT,
                status TEXT,
                created_date TEXT NOT NULL,
                closed_date TEXT,
                days_open INTEGER,
                street_segment TEXT,
                impact_score REAL
            );

            CREATE TABLE IF NOT EXISTS collisions (
                id TEXT PRIMARY KEY,
                crash_date TEXT,
                latitude REAL,
                longitude REAL,
                persons_injured INTEGER DEFAULT 0,
                persons_killed INTEGER DEFAULT 0,
                contributing_factor TEXT
            );

            CREATE TABLE IF NOT EXISTS pothole_collisions (
                pothole_id TEXT REFERENCES potholes(id),
                collision_id TEXT REFERENCES collisions(id),
                distance_m REAL,
                PRIMARY KEY (pothole_id, collision_id)
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pothole_id TEXT REFERENCES potholes(id),
                sent_date TEXT,
                status TEXT DEFAULT 'sent',
                message TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_potholes_status ON potholes(status);
            CREATE INDEX IF NOT EXISTS idx_potholes_borough ON potholes(borough);
            CREATE INDEX IF NOT EXISTS idx_potholes_location ON potholes(latitude, longitude);
            CREATE INDEX IF NOT EXISTS idx_collisions_location ON collisions(latitude, longitude);
            CREATE INDEX IF NOT EXISTS idx_alerts_pothole ON alerts(pothole_id);
        """)
    print(f"Database initialized at {DB_PATH}")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent reads
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
```

**Run it:**
```bash
cd ~/HunterHack/backend
python -m app.database
# Should print: "Database initialized at potholes.db"
```

**Verify:**
```bash
ls potholes.db  # File should exist
```

---

## Phase 2: Data Ingestion (ETL)

### Step 2.1: Create the data fetcher
**What:** Download pothole and collision data from NYC Open Data.

**Create `backend/app/services/etl.py`:**
```python
import pandas as pd
import httpx
import os
from datetime import datetime
from app.database import get_db

NYC_311_API = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
NYC_COLLISIONS_API = "https://data.cityofnewyork.us/resource/h9gi-nx95.json"
NYC_TRAFFIC_API = "https://data.cityofnewyork.us/resource/bf4a-6vgj.json"

APP_TOKEN = os.getenv("NYC_OPENDATA_APP_TOKEN", "")

def fetch_potholes(limit: int = 50000, year_from: str = "2024-01-01") -> pd.DataFrame:
    """Fetch pothole complaints from NYC 311."""
    params = {
        "$where": f"descriptor='Pothole' AND created_date > '{year_from}T00:00:00'",
        "$limit": limit,
        "$order": "created_date DESC",
    }
    if APP_TOKEN:
        params["$$app_token"] = APP_TOKEN

    response = httpx.get(NYC_311_API, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame(data)
    print(f"Fetched {len(df)} pothole records")
    return df

def fetch_collisions(limit: int = 50000, year_from: str = "2024-01-01") -> pd.DataFrame:
    """Fetch motor vehicle collision data."""
    params = {
        "$where": f"latitude IS NOT NULL AND crash_date > '{year_from}'",
        "$limit": limit,
        "$order": "crash_date DESC",
    }
    if APP_TOKEN:
        params["$$app_token"] = APP_TOKEN

    response = httpx.get(NYC_COLLISIONS_API, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame(data)
    print(f"Fetched {len(df)} collision records")
    return df

def clean_potholes(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and validate pothole data."""
    # Keep only rows with valid coordinates
    df = df.dropna(subset=["latitude", "longitude"])

    # Convert types
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    # Filter to NYC bounding box
    df = df[
        (df["latitude"].between(40.4, 41.0)) &
        (df["longitude"].between(-74.3, -73.7))
    ]

    # Normalize status
    df["status"] = df["status"].str.strip().str.lower()

    # Compute days_open
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["closed_date"] = pd.to_datetime(df["closed_date"], errors="coerce")

    now = pd.Timestamp.now()
    df["days_open"] = (df["closed_date"].fillna(now) - df["created_date"]).dt.days
    df["days_open"] = df["days_open"].fillna(0).astype(int)

    # Select needed columns
    columns = ["unique_key", "latitude", "longitude", "borough", "incident_zip",
                "descriptor", "status", "created_date", "closed_date", "days_open"]
    df = df[[c for c in columns if c in df.columns]]

    # Rename to match our schema
    df = df.rename(columns={
        "unique_key": "id",
        "incident_zip": "zip_code",
    })

    df = df.dropna(subset=["id"])
    return df

def clean_collisions(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and validate collision data."""
    df = df.dropna(subset=["latitude", "longitude"])

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    df = df[
        (df["latitude"].between(40.4, 41.0)) &
        (df["longitude"].between(-74.3, -73.7))
    ]

    df["persons_injured"] = pd.to_numeric(df.get("number_of_persons_injured", 0), errors="coerce").fillna(0).astype(int)
    df["persons_killed"] = pd.to_numeric(df.get("number_of_persons_killed", 0), errors="coerce").fillna(0).astype(int)

    columns = ["collision_id", "crash_date", "latitude", "longitude",
                "persons_injured", "persons_killed", "contributing_factor_vehicle_1"]
    df = df[[c for c in columns if c in df.columns]]

    df = df.rename(columns={
        "collision_id": "id",
        "contributing_factor_vehicle_1": "contributing_factor",
    })

    df = df.dropna(subset=["id"])
    return df

def save_potholes_to_db(df: pd.DataFrame):
    """Insert pothole data into SQLite."""
    with get_db() as conn:
        for _, row in df.iterrows():
            conn.execute("""
                INSERT OR REPLACE INTO potholes
                (id, latitude, longitude, borough, zip_code, descriptor, status, created_date, closed_date, days_open)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(row.get("id", "")),
                float(row.get("latitude", 0)),
                float(row.get("longitude", 0)),
                str(row.get("borough", "")),
                str(row.get("zip_code", "")),
                str(row.get("descriptor", "")),
                str(row.get("status", "")),
                str(row.get("created_date", "")),
                str(row.get("closed_date", "")) if pd.notna(row.get("closed_date")) else None,
                int(row.get("days_open", 0)),
            ))
        conn.commit()
    print(f"Saved {len(df)} potholes to database")

def save_collisions_to_db(df: pd.DataFrame):
    """Insert collision data into SQLite."""
    with get_db() as conn:
        for _, row in df.iterrows():
            conn.execute("""
                INSERT OR REPLACE INTO collisions
                (id, crash_date, latitude, longitude, persons_injured, persons_killed, contributing_factor)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(row.get("id", "")),
                str(row.get("crash_date", "")),
                float(row.get("latitude", 0)),
                float(row.get("longitude", 0)),
                int(row.get("persons_injured", 0)),
                int(row.get("persons_killed", 0)),
                str(row.get("contributing_factor", "")),
            ))
        conn.commit()
    print(f"Saved {len(df)} collisions to database")

def run_etl():
    """Full ETL pipeline: fetch, clean, save."""
    print("Starting ETL pipeline...")

    # Step 1: Fetch data
    print("\n1. Fetching pothole data...")
    potholes_df = fetch_potholes(limit=50000, year_from="2024-01-01")

    print("\n2. Fetching collision data...")
    collisions_df = fetch_collisions(limit=50000, year_from="2024-01-01")

    # Step 2: Clean data
    print("\n3. Cleaning pothole data...")
    potholes_df = clean_potholes(potholes_df)

    print("\n4. Cleaning collision data...")
    collisions_df = clean_collisions(collisions_df)

    # Step 3: Save to database
    print("\n5. Saving potholes to database...")
    save_potholes_to_db(potholes_df)

    print("\n6. Saving collisions to database...")
    save_collisions_to_db(collisions_df)

    # Step 4: Run geospatial join
    print("\n7. Running geospatial join...")
    from app.services.geospatial import join_potholes_collisions
    join_potholes_collisions()

    print("\nETL pipeline complete!")

if __name__ == "__main__":
    run_etl()
```

---

### Step 2.2: Create the geospatial join service
**What:** Link collisions to nearby potholes using distance calculations.

**Create `backend/app/services/geospatial.py`:**
```python
import math
from app.database import get_db

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometers using Haversine formula."""
    R = 6371  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def join_potholes_collisions(radius_km: float = 0.025):
    """Find collisions within radius_km of each pothole.

    Default radius: 0.025 km = 25 meters
    """
    with get_db() as conn:
        potholes = conn.execute("""
            SELECT id, latitude, longitude, created_date, closed_date
            FROM potholes
        """).fetchall()

        collisions = conn.execute("""
            SELECT id, crash_date, latitude, longitude
            FROM collisions
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """).fetchall()

    print(f"Joining {len(potholes)} potholes with {len(collisions)} collisions...")

    joined = 0
    with get_db() as conn:
        # Clear existing joins
        conn.execute("DELETE FROM pothole_collisions")

        for pothole in potholes:
            p_id, p_lat, p_lon, p_created, p_closed = pothole

            for collision in collisions:
                c_id, c_date, c_lat, c_lon = collision

                # Quick bounding box check first (much faster than haversine)
                lat_diff = abs(p_lat - c_lat)
                lon_diff = abs(p_lon - c_lon)
                if lat_diff > 0.001 or lon_diff > 0.001:  # ~100m rough check
                    continue

                # Precise distance check
                distance_km = haversine_km(p_lat, p_lon, c_lat, c_lon)
                if distance_km <= radius_km:
                    distance_m = distance_km * 1000
                    conn.execute("""
                        INSERT OR IGNORE INTO pothole_collisions
                        (pothole_id, collision_id, distance_m)
                        VALUES (?, ?, ?)
                    """, (p_id, c_id, round(distance_m, 1)))
                    joined += 1

        conn.commit()

    print(f"Found {joined} pothole-collision pairs within {radius_km*1000:.0f}m")

def update_collision_counts():
    """Update each pothole with its nearby collision count."""
    with get_db() as conn:
        conn.execute("""
            UPDATE potholes SET impact_score = (
                SELECT COUNT(*) * 0.2
                FROM pothole_collisions pc
                WHERE pc.pothole_id = potholes.id
            )
            WHERE impact_score IS NULL
        """)
        conn.commit()
    print("Updated collision-based impact scores")
```

---

## Phase 3: FastAPI Application

### Step 3.1: Create Pydantic schemas
**What:** Define the exact shape of data going in and out of each API endpoint.

**Create `backend/app/schemas.py`:**
```python
from pydantic import BaseModel, Field, validator
from typing import Optional
import re

class PotholeResponse(BaseModel):
    id: str
    latitude: float
    longitude: float
    borough: Optional[str] = None
    zip_code: Optional[str] = None
    descriptor: Optional[str] = None
    status: str
    created_date: str
    closed_date: Optional[str] = None
    days_open: int
    impact_score: Optional[float] = None

class PotholeDetailResponse(PotholeResponse):
    nearby_collision_count: int = 0
    traffic_volume: Optional[int] = None
    accident_risk: str = "LOW"
    accident_risk_probability: float = 0.0
    predicted_repair_days: Optional[int] = None

class PotholeFilterParams(BaseModel):
    borough: Optional[str] = Field(None, pattern="^(Manhattan|Brooklyn|Queens|Bronx|Staten Island)$")
    status: Optional[str] = Field(None, pattern="^(open|closed)$")
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)

class BoroughStats(BaseModel):
    open_count: int
    closed_count: int
    avg_days_open: float
    total_collisions: int

class StatsSummary(BaseModel):
    total_open: int
    total_closed: int
    avg_days_open: float
    by_borough: dict[str, BoroughStats]

class TimelinePoint(BaseModel):
    week: str
    opened: int
    closed: int

class AlertRequest(BaseModel):
    pothole_id: str = Field(..., min_length=1, max_length=50)
    message: Optional[str] = Field(None, max_length=2000)

    @validator("pothole_id")
    def validate_pothole_id(cls, v):
        if not re.match(r"^[a-zA-Z0-9\-]+$", v):
            raise ValueError("Invalid pothole ID format")
        return v

class AlertResponse(BaseModel):
    id: int
    pothole_id: str
    sent_date: str
    status: str
    message: str
```

---

### Step 3.2: Create API endpoints for potholes
**Create `backend/app/api/potholes.py`:**
```python
from fastapi import APIRouter, Query
from app.database import get_db
from app.schemas import PotholeResponse, PotholeDetailResponse, PotholeFilterParams
from app.models.ml_models import predict_for_pothole

router = APIRouter(prefix="/api", tags=["potholes"])

@router.get("/potholes", response_model=list[PotholeResponse])
def get_potholes(
    borough: str | None = Query(None, pattern="^(Manhattan|Brooklyn|Queens|Bronx|Staten Island)$"),
    status: str | None = Query(None, pattern="^(open|closed)$"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Get potholes with optional filters."""
    with get_db() as conn:
        query = "SELECT * FROM potholes WHERE 1=1"
        params = []

        if borough:
            query += " AND borough = ?"
            params.append(borough)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_date DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

@router.get("/potholes/{pothole_id}", response_model=PotholeDetailResponse)
def get_pothole_detail(pothole_id: str):
    """Get detailed info for a single pothole including ML predictions."""
    with get_db() as conn:
        # Get pothole
        row = conn.execute(
            "SELECT * FROM potholes WHERE id = ?", (pothole_id,)
        ).fetchone()

        if not row:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Pothole not found")

        pothole = dict(row)

        # Get collision count
        collision_count = conn.execute(
            "SELECT COUNT(*) FROM pothole_collisions WHERE pothole_id = ?",
            (pothole_id,)
        ).fetchone()[0]

        # Get ML predictions
        predictions = predict_for_pothole(pothole)

        return PotholeDetailResponse(
            **pothole,
            nearby_collision_count=collision_count,
            traffic_volume=predictions.get("traffic_volume"),
            accident_risk=predictions.get("accident_risk", "LOW"),
            accident_risk_probability=predictions.get("accident_risk_probability", 0.0),
            predicted_repair_days=predictions.get("predicted_repair_days"),
        )
```

---

### Step 3.3: Create stats endpoints
**Create `backend/app/api/stats.py`:**
```python
from fastapi import APIRouter
from app.database import get_db
from app.schemas import StatsSummary, BoroughStats, TimelinePoint

router = APIRouter(prefix="/api/stats", tags=["stats"])

@router.get("/summary", response_model=StatsSummary)
def get_stats_summary():
    """Get aggregated pothole statistics."""
    with get_db() as conn:
        # Total counts
        total_open = conn.execute(
            "SELECT COUNT(*) FROM potholes WHERE status = 'open'"
        ).fetchone()[0]

        total_closed = conn.execute(
            "SELECT COUNT(*) FROM potholes WHERE status = 'closed'"
        ).fetchone()[0]

        avg_days = conn.execute(
            "SELECT AVG(days_open) FROM potholes WHERE status = 'open'"
        ).fetchone()[0] or 0

        # Per-borough stats
        boroughs = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
        by_borough = {}

        for borough in boroughs:
            open_count = conn.execute(
                "SELECT COUNT(*) FROM potholes WHERE borough = ? AND status = 'open'",
                (borough,)
            ).fetchone()[0]

            closed_count = conn.execute(
                "SELECT COUNT(*) FROM potholes WHERE borough = ? AND status = 'closed'",
                (borough,)
            ).fetchone()[0]

            avg_borough_days = conn.execute(
                "SELECT AVG(days_open) FROM potholes WHERE borough = ? AND status = 'open'",
                (borough,)
            ).fetchone()[0] or 0

            total_collisions = conn.execute("""
                SELECT COUNT(*) FROM pothole_collisions pc
                JOIN potholes p ON pc.pothole_id = p.id
                WHERE p.borough = ?
            """, (borough,)).fetchone()[0]

            by_borough[borough] = BoroughStats(
                open_count=open_count,
                closed_count=closed_count,
                avg_days_open=round(avg_borough_days, 1),
                total_collisions=total_collisions,
            )

        return StatsSummary(
            total_open=total_open,
            total_closed=total_closed,
            avg_days_open=round(avg_days, 1),
            by_borough=by_borough,
        )

@router.get("/timeline", response_model=list[TimelinePoint])
def get_stats_timeline():
    """Get weekly opened vs closed counts."""
    with get_db() as conn:
        # Get weekly opened counts
        opened = conn.execute("""
            SELECT
                strftime('%Y-%W', created_date) as week,
                COUNT(*) as opened
            FROM potholes
            WHERE created_date > '2024-01-01'
            GROUP BY week
            ORDER BY week
        """).fetchall()

        # Get weekly closed counts
        closed = conn.execute("""
            SELECT
                strftime('%Y-%W', closed_date) as week,
                COUNT(*) as closed
            FROM potholes
            WHERE closed_date IS NOT NULL AND closed_date > '2024-01-01'
            GROUP BY week
            ORDER BY week
        """).fetchall()

        # Merge the two series
        closed_map = {row["week"]: row["closed"] for row in closed}

        return [
            TimelinePoint(
                week=row["week"],
                opened=row["opened"],
                closed=closed_map.get(row["week"], 0),
            )
            for row in opened
        ]
```

---

### Step 3.4: Create prediction endpoints
**Create `backend/app/api/predictions.py`:**
```python
from fastapi import APIRouter
from app.database import get_db
from app.models.ml_models import predict_for_pothole

router = APIRouter(prefix="/api/predictions", tags=["predictions"])

@router.get("/{pothole_id}")
def get_prediction(pothole_id: str):
    """Get ML predictions for a specific pothole."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM potholes WHERE id = ?", (pothole_id,)
        ).fetchone()

        if not row:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Pothole not found")

        pothole = dict(row)
        predictions = predict_for_pothole(pothole)
        return predictions
```

---

### Step 3.5: Create alerts endpoint
**Create `backend/app/api/alerts.py`:**
```python
from fastapi import APIRouter, Depends, Header, HTTPException
from app.database import get_db
from app.schemas import AlertRequest, AlertResponse
from app.services.alert_service import generate_alert_message, send_alert_email
import os
import datetime

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "change-me-in-production")

async def verify_admin_key(x_api_key: str = Header(...)):
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

@router.post("/send", response_model=AlertResponse)
async def send_alert(alert: AlertRequest, authorized: bool = Depends(verify_admin_key)):
    """Send an alert about a high-impact pothole to the DOT."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM potholes WHERE id = ?", (alert.pothole_id,)
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Pothole not found")

        pothole = dict(row)

    # Generate the alert message
    message = generate_alert_message(pothole, alert.message)

    # Try to send (for hackathon, we'll just log it)
    sent = send_alert_email(pothole, message)
    status = "sent" if sent else "failed"

    # Log the alert
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO alerts (pothole_id, sent_date, status, message)
            VALUES (?, ?, ?, ?)
        """, (alert.pothole_id, datetime.datetime.now().isoformat(), status, message))
        alert_id = cursor.lastrowid
        conn.commit()

    return AlertResponse(
        id=alert_id,
        pothole_id=alert.pothole_id,
        sent_date=datetime.datetime.now().isoformat(),
        status=status,
        message=message,
    )

@router.get("/history", response_model=list[AlertResponse])
def get_alert_history():
    """Get history of sent alerts."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM alerts ORDER BY sent_date DESC LIMIT 50"
        ).fetchall()
        return [dict(row) for row in rows]
```

---

### Step 3.6: Create the alert service
**Create `backend/app/services/alert_service.py`:**
```python
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ALERT_RECIPIENT = os.getenv("ALERT_RECIPIENT_EMAIL", "")

def generate_alert_message(pothole: dict, custom_message: str | None = None) -> str:
    """Generate an alert message for a pothole."""
    subject = f"[PotholeTracker] High-Impact Pothole Alert — {pothole.get('borough', 'Unknown')}"

    body = f"""{subject}

Location: ({pothole.get('latitude', 0):.6f}, {pothole.get('longitude', 0):.6f})
Borough: {pothole.get('borough', 'Unknown')}
ZIP: {pothole.get('zip_code', 'Unknown')}
Days Open: {pothole.get('days_open', 0)}
Status: {pothole.get('status', 'unknown')}
Impact Score: {pothole.get('impact_score', 0):.2f if pothole.get('impact_score') else 'N/A'}

{'Additional notes: ' + custom_message if custom_message else ''}

This pothole has been automatically flagged based on impact analysis.
Please prioritize inspection and repair.

— PotholeTracker NYC Automated Alert System
"""
    return body

def send_alert_email(pothole: dict, message: str) -> bool:
    """Send an alert email. Returns True if sent successfully.

    For hackathon: if SMTP is not configured, we log the alert instead.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"[ALERT] Would send email alert for pothole {pothole['id']}:")
        print(message)
        print("---")
        return True  # Pretend it was sent for demo purposes

    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = ALERT_RECIPIENT
        msg["Subject"] = f"[PotholeTracker] Alert — {pothole.get('borough', 'Unknown')}"
        msg.attach(MIMEText(message, "plain"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"[ALERT] Email sent successfully for pothole {pothole['id']}")
        return True
    except Exception as e:
        print(f"[ALERT] Failed to send email: {e}")
        return False
```

---

### Step 3.7: Create the ML models module
**What:** Load trained models and make predictions.

**Create `backend/app/models/ml_models.py`:**
```python
import os
import joblib
import numpy as np
from typing import Optional

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ml")

# Borough encoding mapping
BOROUGH_MAP = {
    "Manhattan": 0,
    "Brooklyn": 1,
    "Queens": 2,
    "Bronx": 3,
    "Staten Island": 4,
}

# Cache loaded models
_accident_model = None
_repair_model = None

def load_accident_model():
    """Load the accident risk classification model."""
    global _accident_model
    if _accident_model is None:
        model_path = os.path.join(MODEL_DIR, "model_accident_risk.pkl")
        if os.path.exists(model_path):
            _accident_model = joblib.load(model_path)
            print(f"Loaded accident risk model from {model_path}")
        else:
            print(f"Warning: Model not found at {model_path}, using heuristic fallback")
    return _accident_model

def load_repair_model():
    """Load the repair timeline regression model."""
    global _repair_model
    if _repair_model is None:
        model_path = os.path.join(MODEL_DIR, "model_repair_timeline.pkl")
        if os.path.exists(model_path):
            _repair_model = joblib.load(model_path)
            print(f"Loaded repair timeline model from {model_path}")
        else:
            print(f"Warning: Model not found at {model_path}, using heuristic fallback")
    return _repair_model

def predict_for_pothole(pothole: dict) -> dict:
    """Generate ML predictions for a single pothole.

    Returns a dict with:
    - accident_risk: "LOW" / "MEDIUM" / "HIGH"
    - accident_risk_probability: float 0-1
    - predicted_repair_days: int or None
    - traffic_volume: int or None
    """
    accident_model = load_accident_model()
    repair_model = load_repair_model()

    days_open = pothole.get("days_open", 0) or 0
    borough = pothole.get("borough", "Manhattan") or "Manhattan"
    impact_score = pothole.get("impact_score") or 0

    # Build feature vector
    borough_encoded = BOROUGH_MAP.get(borough, 0)
    features = np.array([[days_open, borough_encoded, impact_score]])

    # Accident risk prediction
    if accident_model is not None:
        risk_prob = accident_model.predict_proba(features)[0][1]  # Probability of accident
        if risk_prob > 0.6:
            accident_risk = "HIGH"
        elif risk_prob > 0.3:
            accident_risk = "MEDIUM"
        else:
            accident_risk = "LOW"
    else:
        # Heuristic fallback when no model is available
        risk_prob = min(impact_score * 0.3 + days_open * 0.002, 0.95)
        if days_open > 30 and impact_score > 0.5:
            accident_risk = "HIGH"
        elif days_open > 14:
            accident_risk = "MEDIUM"
        else:
            accident_risk = "LOW"

    # Repair timeline prediction
    if repair_model is not None:
        predicted_repair_days = max(1, int(repair_model.predict(features)[0]))
    else:
        # Heuristic fallback
        if borough in ["Manhattan"]:
            predicted_repair_days = max(1, 7 + days_open // 10)
        else:
            predicted_repair_days = max(1, 14 + days_open // 5)

    return {
        "accident_risk": accident_risk,
        "accident_risk_probability": round(float(risk_prob), 3),
        "predicted_repair_days": predicted_repair_days,
        "traffic_volume": None,  # Populated when traffic data is joined
    }
```

---

### Step 3.8: Create the main FastAPI app
**Create `backend/app/main.py`:**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.api import potholes, stats, predictions, alerts

app = FastAPI(
    title="PotholeTracker NYC",
    version="1.0.0",
    description="NYC Pothole tracking, ML prediction, and automated alert system",
)

# CORS — only allow our frontend
ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # Alternative dev port
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Register all API routers
app.include_router(potholes.router)
app.include_router(stats.router)
app.include_router(predictions.router)
app.include_router(alerts.router)

@app.on_event("startup")
def startup():
    """Initialize database on startup."""
    init_db()
    print("PotholeTracker NYC API is ready!")

@app.get("/")
def root():
    return {
        "app": "PotholeTracker NYC",
        "version": "1.0.0",
        "endpoints": {
            "potholes": "/api/potholes",
            "stats": "/api/stats/summary",
            "timeline": "/api/stats/timeline",
            "predictions": "/api/predictions/{pothole_id}",
            "alerts_send": "/api/alerts/send",
            "alerts_history": "/api/alerts/history",
        }
    }
```

**Create `backend/app/api/__init__.py`:**
```python
# Empty init file — makes this a Python package
```

Also create empty `__init__.py` files in:
- `backend/app/__init__.py`
- `backend/app/models/__init__.py`
- `backend/app/services/__init__.py`

---

### Step 3.9: Test the backend
```bash
cd ~/HunterHack/backend
source venv/Scripts/activate

# Start the server
uvicorn app.main:app --reload --port 8000
```

**Verify:**
1. Open http://localhost:8000 in browser — you should see the root endpoint JSON
2. Open http://localhost:8000/docs — you should see the Swagger UI with all endpoints
3. The database file `potholes.db` should be created

**Test the API:**
```bash
# In a new terminal:
curl http://localhost:8000/
curl http://localhost:8000/api/potholes?limit=5
```

---

### Step 3.10: Run ETL to populate data
```bash
cd ~/HunterHack/backend
source venv/Scripts/activate

# Fetch data from NYC Open Data and load into SQLite
python -m app.services.etl
```

This will:
1. Fetch pothole data from NYC 311 API
2. Fetch collision data from NYPD API
3. Clean and validate both datasets
4. Save to SQLite
5. Run geospatial join (potholes ↔ collisions)

**Note:** This step takes 1-5 minutes depending on network speed and data volume.

---

## Phase 4: Machine Learning Pipeline

### Step 4.1: Create feature engineering
**What:** Transform raw pothole data into ML-ready features.

**Create `backend/ml/feature_engineering.py`:**
```python
import pandas as pd
import numpy as np
from app.database import get_db

def build_features():
    """Build ML features from database data.

    Returns a DataFrame with one row per pothole and columns for features.
    """
    with get_db() as conn:
        potholes = pd.read_sql("SELECT * FROM potholes", conn)
        collisions = pd.read_sql("""
            SELECT p.id as pothole_id, COUNT(pc.collision_id) as nearby_collisions
            FROM potholes p
            LEFT JOIN pothole_collisions pc ON p.id = pc.pothole_id
            GROUP BY p.id
        """, conn)

    # Merge collision counts
    df = potholes.merge(collisions, on="pothole_id", how="left")
    df["nearby_collisions"] = df["nearby_collisions"].fillna(0).astype(int)

    # Feature engineering
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["month"] = df["created_date"].dt.month
    df["day_of_week"] = df["created_date"].dt.dayofweek

    # Borough encoding
    borough_map = {
        "Manhattan": 0, "Brooklyn": 1, "Queens": 2,
        "Bronx": 3, "Staten Island": 4,
    }
    df["borough_encoded"] = df["borough"].map(borough_map).fillna(-1).astype(int)

    # Binary target: has nearby collision?
    df["has_nearby_accident"] = (df["nearby_collisions"] > 0).astype(int)

    # For repair timeline: only closed potholes
    df["days_to_close"] = None
    closed_mask = df["status"] == "closed"
    if closed_mask.any():
        df.loc[closed_mask, "closed_date"] = pd.to_datetime(
            df.loc[closed_mask, "closed_date"], errors="coerce"
        )
        df.loc[closed_mask, "days_to_close"] = (
            df.loc[closed_mask, "closed_date"] - df.loc[closed_mask, "created_date"]
        ).dt.days

    # Traffic volume (proxy: use borough average if not available)
    # For hackathon, use a simple proxy based on borough
    borough_traffic = {
        "Manhattan": 25000,
        "Brooklyn": 15000,
        "Queens": 18000,
        "Bronx": 12000,
        "Staten Island": 8000,
    }
    df["traffic_volume_aadt"] = df["borough"].map(borough_traffic)

    # Nearby pothole count (within 100m — approximate with zip code for speed)
    pothole_counts_by_zip = df.groupby("zip_code").size().reset_index(name="nearby_pothole_count")
    df = df.merge(pothole_counts_by_zip, on="zip_code", how="left")
    df["nearby_pothole_count"] = df["nearby_pothole_count"].fillna(1).astype(int)

    # Select final feature columns
    feature_cols = [
        "pothole_id", "days_open", "borough_encoded", "traffic_volume_aadt",
        "nearby_pothole_count", "month", "day_of_week", "latitude", "longitude",
        "has_nearby_accident", "nearby_collisions", "days_to_close", "status"
    ]

    df = df[[c for c in feature_cols if c in df.columns]]

    # Save to CSV for inspection
    df.to_csv("data/processed/features.csv", index=False)
    print(f"Built features for {len(df)} potholes → data/processed/features.csv")

    return df

if __name__ == "__main__":
    build_features()
```

---

### Step 4.2: Train the accident risk model
**Create `backend/ml/train_accident_risk.py`:**
```python
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import xgboost as xgb
import joblib
import os

def train_accident_risk_model():
    """Train XGBoost classifier to predict accident risk near a pothole."""
    print("Training Accident Risk Model...")

    # Load features
    df = pd.read_csv("data/processed/features.csv")

    # Features for prediction
    feature_cols = [
        "days_open", "borough_encoded", "traffic_volume_aadt",
        "nearby_pothole_count", "month", "day_of_week",
        "latitude", "longitude",
    ]

    X = df[feature_cols].fillna(0)
    y = df["has_nearby_accident"]

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Train model
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        eval_metric="logloss",
        use_label_encoder=False,
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    try:
        auc = roc_auc_score(y_test, y_prob)
        print(f"ROC-AUC: {auc:.3f}")
    except ValueError:
        print("ROC-AUC: Could not compute (possible single class in test set)")

    # Feature importance
    importance = pd.Series(model.feature_importances_, index=feature_cols)
    print("\nFeature Importance:")
    print(importance.sort_values(ascending=False))

    # Save model
    model_path = os.path.join(os.path.dirname(__file__), "model_accident_risk.pkl")
    joblib.dump(model, model_path)
    print(f"\nModel saved to {model_path}")

    return model

if __name__ == "__main__":
    train_accident_risk_model()
```

---

### Step 4.3: Train the repair timeline model
**Create `backend/ml/train_repair_timeline.py`:**
```python
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import xgboost as xgb
import joblib
import os

def train_repair_timeline_model():
    """Train XGBoost regressor to predict repair timeline for a pothole."""
    print("Training Repair Timeline Model...")

    # Load features
    df = pd.read_csv("data/processed/features.csv")

    # Only use closed potholes (we know how long they took to close)
    closed = df[df["status"] == "closed"].copy()
    closed = closed.dropna(subset=["days_to_close"])

    if len(closed) < 50:
        print(f"Warning: Only {len(closed)} closed potholes for training. Using heuristic fallback.")
        # Save a dummy model that uses heuristics
        model_path = os.path.join(os.path.dirname(__file__), "model_repair_timeline.pkl")
        joblib.dump(None, model_path)
        return None

    feature_cols = [
        "days_open", "borough_encoded", "traffic_volume_aadt",
        "nearby_pothole_count", "month",
        "nearby_collisions",
    ]

    X = closed[feature_cols].fillna(0)
    y = closed["days_to_close"]

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Train model
    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    print(f"\nMean Absolute Error: {mae:.1f} days")
    print(f"Root Mean Squared Error: {rmse:.1f} days")

    # Feature importance
    importance = pd.Series(model.feature_importances_, index=feature_cols)
    print("\nFeature Importance:")
    print(importance.sort_values(ascending=False))

    # Save model
    model_path = os.path.join(os.path.dirname(__file__), "model_repair_timeline.pkl")
    joblib.dump(model, model_path)
    print(f"\nModel saved to {model_path}")

    return model

if __name__ == "__main__":
    train_repair_timeline_model()
```

---

### Step 4.4: Run the full ML pipeline
```bash
cd ~/HunterHack/backend
source venv/Scripts/activate

# Step 1: Build features from database data
python -m ml.feature_engineering

# Step 2: Train accident risk model
python -m ml.train_accident_risk

# Step 3: Train repair timeline model
python -m ml.train_repair_timeline
```

**Verify:**
```bash
ls ml/*.pkl
# Should show:
# model_accident_risk.pkl
# model_repair_timeline.pkl

ls data/processed/features.csv
# Should show the feature CSV
```

---

## Phase 5: Impact Score Computation

### Step 5.1: Update impact scores in the database
**Create `backend/app/services/impact.py`:**
```python
from app.database import get_db
from app.models.ml_models import predict_for_pothole

def compute_impact_scores():
    """Calculate and update impact scores for all open potholes."""
    with get_db() as conn:
        potholes = conn.execute("""
            SELECT id, days_open, borough, impact_score
            FROM potholes WHERE status = 'open'
        """).fetchall()

    print(f"Computing impact scores for {len(potholes)} open potholes...")

    for pothole in potholes:
        p = dict(pothole)
        predictions = predict_for_pothole(p)

        # Composite impact score
        accident_prob = predictions["accident_risk_probability"]
        days_normalized = min(p.get("days_open", 0) / 90, 1)  # Normalize to 0-1

        impact_score = (
            0.4 * accident_prob +       # Accident risk weight
            0.3 * days_normalized +      # Days open weight
            0.3 * (predictions.get("traffic_volume") or 0) / 25000  # Traffic weight
        )

        with get_db() as conn:
            conn.execute(
                "UPDATE potholes SET impact_score = ? WHERE id = ?",
                (round(impact_score, 3), p["id"])
            )
            conn.commit()

    print("Impact scores updated!")

if __name__ == "__main__":
    compute_impact_scores()
```

**Run it:**
```bash
cd ~/HunterHack/backend
source venv/Scripts/activate
python -m app.services.impact
```

---

## Phase 6: Deploy the Backend

### Step 6.1: Deploy to Render (free tier)
1. Push your code to GitHub
2. Go to https://render.com/ and sign up
3. Click "New Web Service"
4. Connect your GitHub repo
5. Settings:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables:** Copy all from your `.env` file
6. Click "Create Web Service"

### Step 6.2: Update frontend to point to deployed backend
**Edit `frontend/.env`:**
```
VITE_API_BASE_URL=https://your-backend.onrender.com
```

---

## Verification Checklist

After completing all backend steps:

- [ ] `potholes.db` exists and has data
- [ ] `uvicorn app.main:app --reload` starts without errors
- [ ] `GET /` returns the API info JSON
- [ ] `GET /api/potholes?limit=5` returns pothole data
- [ ] `GET /api/potholes/{id}` returns detailed pothole with ML predictions
- [ ] `GET /api/stats/summary` returns borough-level stats
- [ ] `GET /api/stats/timeline` returns weekly time series
- [ ] `GET /api/predictions/{id}` returns accident risk and repair ETA
- [ ] `POST /api/alerts/send` with valid API key creates an alert
- [ ] `GET /api/alerts/history` returns alert history
- [ ] `ml/model_accident_risk.pkl` exists
- [ ] `ml/model_repair_timeline.pkl` exists
- [ ] Swagger UI at `/docs` shows all endpoints