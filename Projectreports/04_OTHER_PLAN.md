# Other (Project Management, Data, DevOps, Demo) — PotholeTracker NYC

> **Audience:** Beginners who just started coding. Every step is explicit.

---

## Phase 0: Project Coordination

### Step 0.1: Split work among team members
**What:** Decide who does what so you don't step on each other.

**Suggested split for a 3-4 person team:**

| Role | Person | Focus |
|------|--------|-------|
| Frontend | Person A — Taskin | Map, tooltips, detail panel, dashboard, animations |
| Backend + ML | Person B — Kevin | API, database, ETL, model training, predictions |
| Full-stack + Security | Person C — Kazi | Alert system, security, CORS, validation, integration |
| Data + Polish | Person D — Rakhmonjon | Data fetching, testing, demo prep, deployment |

**If you're 2-3 people:** Combine roles. Frontend person does all UI. Backend person does all API + ML. Both handle their own deployment.

---

### Step 0.2: Set up branch workflow
**What:** Use Git branches so you don't overwrite each other's work.

```bash
# Each person creates their own branch:
cd ~/HunterHack
git checkout -b frontend     # Frontend person
git checkout -b backend       # Backend person
git checkout -b integration   # Integration person

# When you finish a feature:
git add .
git commit -m "Add pothole map component"
git push origin frontend

# Merge to main when feature is working:
# Go to GitHub → Pull Requests → Create PR → Merge
```

**Rule:** Never push directly to `main` during active development. Always use a branch and merge via Pull Request.

---

### Step 0.3: Daily standup format
**What:** 5-minute check-in to stay aligned.

**Format (use your team chat or a shared doc):**
```
1. What I did yesterday
2. What I'm doing today
3. Any blockers
```

**Example:**
```
Yesterday: Set up FastAPI server, fetched 311 data
Today: Building the /api/potholes endpoint
Blockers: None
```

---

## Phase 1: Data Acquisition

### Step 1.1: Get NYC Open Data App Token (optional but recommended)
**What:** An app token raises your API rate limit from 1,000 to 50,000 requests per hour.

**How:**
1. Go to https://data.cityofnewyork.us/
2. Click "Sign Up" (top right)
3. Fill in your info
4. Go to https://data.cityofnewyork.us/profile/edit/developer_settings
5. Click "Create App Token"
6. Copy the token and add to your `.env`:
```
NYC_OPENDATA_APP_TOKEN=your_token_here
```

**Without a token:** The API still works, but rate-limited to ~1,000 requests/hour. Fine for a hackathon.

---

### Step 1.2: Download and cache raw data
**What:** Fetch data once and save locally so you're not hitting the API repeatedly during development.

**Create `backend/scripts/fetch_data.py`:**
```python
"""Standalone script to download and cache NYC Open Data."""
import httpx
import pandas as pd
import os

DATA_DIR = "data/raw"
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_and_save(dataset_name: str, url: str, params: dict, filename: str):
    """Fetch data from NYC Open Data and save as CSV."""
    print(f"Fetching {dataset_name}...")
    response = httpx.get(url, params=params, timeout=120)
    response.raise_for_status()

    df = pd.DataFrame(response.json())
    filepath = os.path.join(DATA_DIR, filename)
    df.to_csv(filepath, index=False)
    print(f"  Saved {len(df)} rows to {filepath}")
    return df

if __name__ == "__main__":
    # Potholes
    fetch_and_save(
        "311 Pothole Complaints",
        "https://data.cityofnewyork.us/resource/erm2-nwe9.json",
        {"$where": "descriptor='Pothole' AND created_date > '2024-01-01T00:00:00'", "$limit": 50000},
        "potholes.csv"
    )

    # Collisions
    fetch_and_save(
        "Motor Vehicle Collisions",
        "https://data.cityofnewyork.us/resource/h9gi-nx95.json",
        {"$where": "latitude IS NOT NULL AND crash_date > '2024-01-01'", "$limit": 50000},
        "collisions.csv"
    )

    # Traffic
    fetch_and_save(
        "Traffic Volume",
        "https://data.cityofnewyork.us/resource/bf4a-6vgj.json",
        {"$limit": 50000},
        "traffic.csv"
    )

    print("\nAll data fetched! Files are in data/raw/")
```

**Run it:**
```bash
cd ~/HunterHack/backend
source venv/Scripts/activate
python scripts/fetch_data.py
```

**Verify:**
```bash
ls data/raw/
# Should show: potholes.csv, collisions.csv, traffic.csv

wc -l data/raw/*.csv
# Should show thousands of rows in each
```

---

### Step 1.3: Explore your data (quick sanity check)
**What:** Verify the data looks correct before building on top of it.

**Create `backend/scripts/explore_data.py`:**
```python
"""Quick data exploration — run this once to understand your data."""
import pandas as pd

print("=" * 60)
print("POTHOLE DATA")
print("=" * 60)
potholes = pd.read_csv("data/raw/potholes.csv")
print(f"Rows: {len(potholes)}")
print(f"Columns: {list(potholes.columns)}")
print(f"\nStatus distribution:")
print(potholes["status"].value_counts() if "status" in potholes.columns else "No status column")
print(f"\nBorough distribution:")
print(potholes["borough"].value_counts() if "borough" in potholes.columns else "No borough column")
print(f"\nFirst 3 rows:")
print(potholes.head(3))

print("\n" + "=" * 60)
print("COLLISION DATA")
print("=" * 60)
collisions = pd.read_csv("data/raw/collisions.csv")
print(f"Rows: {len(collisions)}")
print(f"Columns: {list(collisions.columns)}")
print(f"\nFirst 3 rows:")
print(collisions.head(3))
```

**Run it:**
```bash
python scripts/explore_data.py
```

Review the output. Key things to check:
- Do you have rows? (Should be thousands)
- Are latitude/longitude columns present and populated?
- Are borough values correct? (Should be 5 NYC boroughs + possible NaN)

---

## Phase 2: Testing

### Step 2.1: Install testing dependencies
```bash
cd ~/HunterHack/backend
source venv/Scripts/activate
pip install pytest pytest-asyncio httpx
```

Add to `requirements.txt`:
```
pytest==8.3.0
pytest-asyncio==0.24.0
```

---

### Step 2.2: Write API tests
**Create `backend/tests/test_api.py`:**
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    """Root endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "app" in data
    assert data["app"] == "PotholeTracker NYC"

def test_get_potholes():
    """GET /api/potholes returns a list."""
    response = client.get("/api/potholes?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_potholes_with_borough_filter():
    """GET /api/potholes?borough=Manhattan filters correctly."""
    response = client.get("/api/potholes?borough=Manhattan&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for pothole in data:
        assert pothole["borough"] == "Manhattan"

def test_get_potholes_with_status_filter():
    """GET /api/potholes?status=open filters correctly."""
    response = client.get("/api/potholes?status=open&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for pothole in data:
        assert pothole["status"] == "open"

def test_get_stats_summary():
    """GET /api/stats/summary returns borough stats."""
    response = client.get("/api/stats/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_open" in data
    assert "total_closed" in data
    assert "by_borough" in data

def test_get_stats_timeline():
    """GET /api/stats/timeline returns time series."""
    response = client.get("/api/stats/timeline")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_invalid_borough_rejected():
    """Invalid borough parameter is rejected."""
    response = client.get("/api/potholes?borough=InvalidCity")
    assert response.status_code == 422  # Validation error

def test_invalid_status_rejected():
    """Invalid status parameter is rejected."""
    response = client.get("/api/potholes?status=maybe")
    assert response.status_code == 422
```

---

### Step 2.3: Write ML model tests
**Create `backend/tests/test_ml.py`:**
```python
import pytest
import numpy as np
from app.models.ml_models import predict_for_pothole, BOROUGH_MAP

def test_predict_for_pothole_returns_required_fields():
    """Prediction returns all required fields."""
    pothole = {
        "id": "12345",
        "days_open": 30,
        "borough": "Manhattan",
        "impact_score": 0.7,
        "latitude": 40.7128,
        "longitude": -74.006,
    }
    result = predict_for_pothole(pothole)

    assert "accident_risk" in result
    assert "accident_risk_probability" in result
    assert "predicted_repair_days" in result
    assert result["accident_risk"] in ["LOW", "MEDIUM", "HIGH"]
    assert 0 <= result["accident_risk_probability"] <= 1
    assert isinstance(result["predicted_repair_days"], int)

def test_predict_risk_levels():
    """Risk levels are assigned correctly based on features."""
    # High-risk pothole
    high_risk = predict_for_pothole({
        "id": "1", "days_open": 60, "borough": "Manhattan",
        "impact_score": 0.8, "latitude": 40.7, "longitude": -74.0,
    })

    # Low-risk pothole
    low_risk = predict_for_pothole({
        "id": "2", "days_open": 2, "borough": "Staten Island",
        "impact_score": 0.1, "latitude": 40.5, "longitude": -74.1,
    })

    # High-risk should have higher probability than low-risk
    # (With heuristic fallback, this should always hold)
    assert high_risk["accident_risk_probability"] >= low_risk["accident_risk_probability"]

def test_borough_mapping():
    """Borough encoding maps correctly."""
    assert "Manhattan" in BOROUGH_MAP
    assert "Brooklyn" in BOROUGH_MAP
    assert "Queens" in BOROUGH_MAP
    assert "Bronx" in BOROUGH_MAP
    assert "Staten Island" in BOROUGH_MAP
```

---

### Step 2.4: Run the tests
```bash
cd ~/HunterHack/backend
source venv/Scripts/activate
pytest tests/ -v
```

**All tests should pass.** If any fail, read the error message and fix the issue.

---

### Step 2.5: Frontend testing (manual checklist)
Since we're in a hackathon, manual testing is faster than writing frontend unit tests. Use this checklist:

```markdown
## Frontend Manual Test Checklist

### Map Page
- [ ] Map loads centered on NYC
- [ ] Pothole dots appear on the map
- [ ] Dots are color-coded (red/amber/green/gray)
- [ ] Hovering over a dot shows a tooltip
- [ ] Tooltip shows pothole ID, days open, borough
- [ ] Clicking a dot opens the detail panel
- [ ] Detail panel slides in from the right
- [ ] Detail panel shows ML predictions
- [ ] "Alert DOT" button is visible for open potholes
- [ ] Closing the detail panel works (X button)

### Dashboard Page
- [ ] Summary cards show correct numbers
- [ ] Borough breakdown bars render
- [ ] Weekly chart shows opened vs closed bars
- [ ] Data refreshes when navigating back to dashboard

### Filters
- [ ] Borough dropdown filters the map
- [ ] Status dropdown filters the map
- [ ] Filters reset correctly

### Error States
- [ ] Loading spinner appears while data fetches
- [ ] Error message appears if backend is down
- [ ] Retry button on error message works

### Mobile
- [ ] Map takes full screen on mobile
- [ ] Detail panel overlays on mobile (not side-by-side)
- [ ] Filters stack vertically on small screens
```

---

## Phase 3: Demo Preparation

### Step 3.1: Create a demo script
**What:** A step-by-step script for your hackathon demo. Practice it 2-3 times.

**Create `Projectreports/DEMO_SCRIPT.md`:**
```markdown
# PotholeTracker NYC — Demo Script (5 minutes)

## 1. Problem Statement (30 seconds)
"NYC has thousands of potholes. Citizens can't see which ones are dangerous,
and the city lacks data-driven prioritization. We built PotholeTracker NYC."

## 2. Map Demo (90 seconds)
- Open the app → show the map with colored dots
- Zoom into Manhattan → point out red (critical) dots
- Hover over a pothole → show tooltip with days open
- Click a pothole → show detail panel with ML predictions
  - "This pothole has been open for 47 days"
  - "Our model predicts HIGH accident risk — 73% probability"
  - "Estimated repair time: 12 days"

## 3. Dashboard (60 seconds)
- Switch to Dashboard view
- Show summary cards: total open, closed, avg days open
- Show borough breakdown
- Show timeline chart (opened vs closed per week)

## 4. Alert System (60 seconds)
- Go back to a high-impact pothole
- Click "Alert DOT Department"
- Show the generated alert message
- Explain: "This automatically sends data-backed notifications to the DOT
  with urgency metrics — daily vehicles affected, accident risk, repair ETA"

## 5. Technical Highlights (60 seconds)
- "Built with React + Leaflet for smooth map interactions"
- "FastAPI backend with SQLite for fast queries"
- "XGBoost models predict accident risk and repair timelines"
- "Impact scoring combines ML predictions with traffic volume"
- "Automated alert system with data-backed prioritization"

## 6. Closing (30 seconds)
"We believe data-driven pothole prioritization can save lives and
reduce vehicle damage. Thank you."
```

---

### Step 3.2: Seed demo data (if needed)
**What:** If the live NYC API is down during your demo, have backup data.

**Create `backend/scripts/seed_demo_data.py`:**
```python
"""Generate sample data for demo purposes if NYC API is unavailable."""
import sqlite3
import random
import datetime
from app.database import init_db, get_db

BOROUGHS = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
DESCRIPTORS = [
    "Pothole", "Large pothole", "Deep pothole in middle of lane",
    "Multiple potholes", "Pothole causing tire damage",
    "Pothole at intersection", "Pothole near crosswalk",
]

def generate_demo_data():
    init_db()

    with get_db() as conn:
        # Clear existing data
        conn.execute("DELETE FROM pothole_collisions")
        conn.execute("DELETE FROM collisions")
        conn.execute("DELETE FROM potholes")
        conn.execute("DELETE FROM alerts")

        # Generate 500 potholes across NYC
        for i in range(500):
            borough = random.choice(BOROUGHS)
            # Approximate bounding boxes for each borough
            lat_ranges = {
                "Manhattan": (40.700, 40.880),
                "Brooklyn": (40.570, 40.740),
                "Queens": (40.540, 40.800),
                "Bronx": (40.785, 40.920),
                "Staten Island": (40.490, 40.650),
            }
            lon_ranges = {
                "Manhattan": (-74.020, -73.910),
                "Brooklyn": (-74.040, -73.830),
                "Queens": (-73.960, -73.700),
                "Bronx": (-73.930, -73.760),
                "Staten Island": (-74.250, -74.080),
            }

            lat = random.uniform(*lat_ranges[borough])
            lon = random.uniform(*lon_ranges[borough])

            days_open = random.randint(1, 90)
            status = "open" if random.random() > 0.3 else "closed"
            created = datetime.datetime.now() - datetime.timedelta(days=days_open)
            closed = None
            if status == "closed":
                closed_days = random.randint(1, days_open)
                closed = (created + datetime.timedelta(days=closed_days)).isoformat()

            impact = random.uniform(0, 1) if status == "open" else random.uniform(0, 0.3)

            conn.execute("""
                INSERT INTO potholes (id, latitude, longitude, borough, zip_code, descriptor, status, created_date, closed_date, days_open, impact_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"DEMO-{i:05d}",
                round(lat, 6), round(lon, 6),
                borough, f"{random.randint(10000, 11699)}",
                random.choice(DESCRIPTORS),
                status,
                created.isoformat(), closed,
                days_open, round(impact, 3),
            ))

        # Generate some collisions
        for i in range(200):
            borough = random.choice(BOROUGHS)
            lat = random.uniform(*lat_ranges[borough])
            lon = random.uniform(*lon_ranges[borough])

            conn.execute("""
                INSERT INTO collisions (id, crash_date, latitude, longitude, persons_injured, persons_killed, contributing_factor)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                f"COL-{i:05d}",
                (datetime.datetime.now() - datetime.timedelta(days=random.randint(1, 180))).isoformat(),
                round(lat, 6), round(lon, 6),
                random.randint(0, 3), random.choice([0, 0, 0, 0, 1]),
                random.choice(["Driver Inattention", "Pothole", "Pavement Defect", "Other"]),
            ))

        conn.commit()

    print("Demo data generated! 500 potholes + 200 collisions")
    print("Run 'uvicorn app.main:app --reload' to start the server")

if __name__ == "__main__":
    generate_demo_data()
```

**Run it:**
```bash
cd ~/HunterHack/backend
source venv/Scripts/activate
python scripts/seed_demo_data.py
```

---

### Step 3.3: Practice the demo
1. Start backend: `uvicorn app.main:app --reload`
2. Start frontend: `cd ../frontend && npm run dev`
3. Open http://localhost:5173
4. Walk through the demo script out loud
5. Time yourself — aim for 5 minutes
6. Practice handling: "What if the API is slow?" → Show the loading spinner
7. Practice handling: "What about mobile?" → Open browser dev tools → toggle responsive mode

---

## Phase 4: Deployment

### Step 4.1: Backend deployment checklist
```markdown
## Backend Deployment (Render)

1. Push code to GitHub
2. Go to render.com → New Web Service
3. Connect your repo
4. Settings:
   - Root Directory: backend
   - Build Command: pip install -r requirements.txt
   - Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
5. Add environment variables:
   - DATABASE_URL = sqlite:///./potholes.db
   - SECRET_KEY = (generate a random 32-char string)
   - ALLOWED_ORIGINS = https://your-frontend.vercel.app
   - ADMIN_API_KEY = (generate a random string)
6. Deploy
7. Verify: Open https://your-backend.onrender.com/docs
```

### Step 4.2: Frontend deployment checklist
```markdown
## Frontend Deployment (Vercel)

1. Push code to GitHub
2. Go to vercel.com → New Project
3. Import your repo
4. Settings:
   - Root Directory: frontend
   - Framework: Vite
5. Add environment variables:
   - VITE_API_BASE_URL = https://your-backend.onrender.com
   - VITE_MAPBOX_TOKEN = (your public token, if using Mapbox)
6. Deploy
7. Verify: Open the Vercel URL
8. Test the full flow: map → click pothole → see predictions → alert
```

### Step 4.3: Post-deployment verification
```bash
# Check backend is alive
curl https://your-backend.onrender.com/

# Check API returns data
curl https://your-backend.onrender.com/api/potholes?limit=5

# Check frontend loads
curl https://your-frontend.vercel.app/

# Open frontend in browser and do full walkthrough
```

---

## Phase 5: Presentation Materials

### Step 5.1: Create a simple pitch deck (5-7 slides)
```markdown
# Slide 1: Title
PotholeTracker NYC
Real-time pothole tracking, ML prediction, and automated alerts

# Slide 2: Problem
- NYC receives 200,000+ pothole complaints per year
- Citizens can't see which potholes are most dangerous
- DOT lacks data-driven prioritization
- Result: dangerous potholes stay open for months

# Slide 3: Solution
- Interactive map showing all open/closed potholes
- ML-powered accident risk and repair timeline predictions
- Automated DOT alerts with data-backed urgency metrics
- Impact scoring: traffic volume × accident risk × days open

# Slide 4: How It Works (Architecture Diagram)
[Show the architecture diagram from the project report]

# Slide 5: ML Models
- Accident Risk Classifier: Predicts if a pothole will cause an accident
  - Features: days open, borough, traffic volume, nearby potholes, month
  - Output: LOW / MEDIUM / HIGH risk with probability
- Repair Timeline Regressor: Predicts when a pothole will be fixed
  - Features: days open, borough, traffic, nearby collisions
  - Output: Estimated days until repair

# Slide 6: Demo
[Live demo of the app]

# Slide 7: Future Work
- Real-time 311 integration for live updates
- Mobile app with pothole photo reporting
- Expand to other cities with open data
- Integration with Waze/Google Maps for rerouting
```

---

### Step 5.2: Update the main README
**Edit `~/HunterHack/README.md`** with project info, setup instructions, and links:

```markdown
# PotholeTracker NYC

Real-time NYC pothole tracking with ML-powered accident prediction and automated DOT alerts.

## Quick Start

### Backend
```bash
cd backend
python -m venv venv
source venv/Scripts/activate  # Windows
pip install -r requirements.txt
python -m app.database          # Initialize database
python -m app.services.etl      # Fetch & process data
uvicorn app.main:app --reload   # Start server
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### ML Training
```bash
cd backend
source venv/Scripts/activate
python -m ml.feature_engineering
python -m ml.train_accident_risk
python -m ml.train_repair_timeline
```

## Architecture
[Link to architecture diagram]

## Team
- [Name] — Frontend
- [Name] — Backend & ML
- [Name] — Integration & Security
```

---

## Phase 6: Hackathon Day Checklist

### Before the Hackathon
- [ ] All team members have Python 3.11+, Node.js 18+, and Git installed
- [ ] Everyone has cloned the repo and can run `npm run dev` and `uvicorn`
- [ ] Everyone has a `.env` file with the correct values
- [ ] NYC Open Data API is accessible (test with a curl command)
- [ ] Team roles are assigned

### During the Hackathon (Hour-by-Hour)
```
Hour 0-2:   Set up project structure, install deps, fetch data
Hour 2-4:   Backend API endpoints, database schema, basic ETL
Hour 4-6:   Frontend map with markers, tooltip on hover
Hour 6-8:   Geospatial join, ML feature engineering
Hour 8-10:  ML model training, predictions endpoint
Hour 10-12: Detail panel, dashboard charts
Hour 12-14: Alert system, impact scoring
Hour 14-16: Polish animations, mobile responsiveness
Hour 16-18: Testing, bug fixes, security hardening
Hour 18-20: Deploy to Vercel + Render
Hour 20-22: Practice demo (2-3 run-throughs)
Hour 22-24: Final polish, README, submit
```

### Common Issues & Quick Fixes
| Problem | Quick Fix |
|---------|-----------|
| `ModuleNotFoundError` | Make sure venv is activated: `source venv/Scripts/activate` |
| `npm ERR!` | Delete `node_modules` and `package-lock.json`, then `npm install` |
| CORS error in browser | Check `ALLOWED_ORIGINS` in backend `.env` includes your frontend URL |
| Empty map / no markers | Check backend is running and returning data: `curl localhost:8000/api/potholes?limit=5` |
| `Address already in use` | Kill the process on that port: `lsof -ti:8000 | xargs kill` (Mac/Linux) or find it in Task Manager (Windows) |
| Data not loading | Run ETL script again: `python -m app.services.etl` |
| Map not rendering | Check browser console for errors; make sure Leaflet CSS is imported |

---

## Quick Reference: All Commands

```bash
# === BACKEND ===
cd ~/HunterHack/backend
source venv/Scripts/activate          # Activate venv
python -m app.database                # Initialize DB
python -m app.services.etl            # Fetch & load data
python -m app.services.impact         # Compute impact scores
python -m ml.feature_engineering      # Build ML features
python -m ml.train_accident_risk      # Train accident model
python -m ml.train_repair_timeline    # Train repair model
uvicorn app.main:app --reload         # Start API server
pytest tests/ -v                      # Run tests

# === FRONTEND ===
cd ~/HunterHack/frontend
npm install                           # Install deps
npm run dev                           # Start dev server
npm run build                         # Production build
npm run preview                       # Preview production build

# === DATA ===
python scripts/fetch_data.py           # Download raw data
python scripts/explore_data.py         # Explore data
python scripts/seed_demo_data.py       # Generate demo data

# === GIT ===
git add .
git commit -m "description"
git push origin <branch-name>
```