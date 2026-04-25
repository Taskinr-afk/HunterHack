# PotholeTracker NYC — Hackathon Project Report

## 1. Project Overview

**Problem:** NYC potholes cause vehicle damage, accidents, and traffic disruptions. Citizens lack visibility into pothole status, and the city lacks an automated, data-driven prioritization system.

**Solution:** An interactive web application that maps NYC potholes, predicts accident risk and repair timelines using ML, and automatically alerts the local sanitation/DOT department with urgency metrics.

**Core Value Props:**
- Citizens see real-time pothole status on an interactive map
- ML predicts accident risk and repair timelines per pothole
- Automated alerts to NYC DOT with data-backed urgency (daily affected vehicles, accident risk)

---

## 2. Data Sources

### 2.1 Primary: NYC 311 Service Requests (Potholes)
- **Dataset:** [311 Service Requests from 2010 to Present](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2010-to-Present/erm2-nwe9)
- **Filter:** `Complaint Type = "Street Condition"` / `Descriptor = "Pothole"`
- **Key fields:**
  - `unique_key` — pothole ID
  - `created_date` — when the complaint was filed
  - `closed_date` — when it was resolved (null = still open)
  - `borough`, `zip`, `latitude`, `longitude` — location
  - `descriptor` — pothole specifics
  - `status` — open/closed
- **API:** SODA API — `https://data.cityofnewyork.us/resource/erm2-nwe9.json?$where=descriptor='Pothole'`

### 2.2 Supplementary: NYPD Motor Vehicle Collisions
- **Dataset:** [Motor Vehicle Collisions - Crashes](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95)
- **Use:** Cross-reference collision locations with pothole locations to derive accident counts/costs per pothole
- **Key fields:** `collision_id`, `crash_date`, `latitude`, `longitude`, `number_of_persons_injured`, `number_of_persons_killed`, `contributing_factor`
- **Join strategy:** Geospatial join — collisions within ~25m radius of a pothole, filtered to dates while the pothole was open

### 2.3 Supplementary: Traffic Volume
- **Option A (free):** [NYC DOT Traffic Counts](https://data.cityofnewyork.us/Transportation/Traffic-Volume-Counts-2014-2019-/bf4a-6vgj) — annual average daily traffic (AADT) by street segment
- **Option B (API):** Google Maps Directions API / Distance Matrix API — derive reroute volume by querying typical traffic on affected segments
- **Option C (hackathon shortcut):** Use NYC DOT traffic counts for a proxy — assign each pothole the AADT of its street segment

### 2.4 Supplementary: Road/Street Geometry
- **Dataset:** [NYC Street Centerline (CSCL)](https://data.cityofnewyork.us/City-Government/NYC-Street-Centerline-CSCL-/exjm-f27b)
- **Use:** Map potholes to specific street segments for traffic volume matching

### 2.5 Data Pipeline Summary
```
311 Potholes ──┐
               ├─► Geospatial Join ─► Enriched Pothole Records
Collisions ────┘          │
                           ├── Traffic Volume Join
                           └── Street Segment Join
```

---

## 3. System Architecture

```
┌──────────────────────────────────────────────────────┐
│                     Frontend                          │
│  ┌─────────┐  ┌──────────┐  ┌─────────────────────┐  │
│  │ Map View │  │ Dashboard│  │ Alert Status Panel  │  │
│  │(pothole  │  │(stats &  │  │(show sent alerts &  │  │
│  │  dots)   │  │ charts)  │  │ DOT responses)      │  │
│  └────┬─────┘  └────┬─────┘  └──────────┬──────────┘  │
│       │              │                    │             │
│       └──────────────┴────────────────────┘             │
│                         │                              │
│                   REST API Calls                       │
└─────────────────────────┬──────────────────────────────┘
                          │
┌─────────────────────────┴──────────────────────────────┐
│                     Backend (Flask/FastAPI)            │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Data      │  │ ML Service   │  │ Alert Service   │  │
│  │ Ingestion │  │ (predictions)│  │ (DOT notifier)  │  │
│  │ & ETL     │  │              │  │                  │  │
│  └─────┬─────┘  └──────┬───────┘  └───────┬─────────┘  │
│        │               │                   │            │
│        └───────────────┴───────────────────┘            │
│                         │                              │
│                    Database                            │
│              (PostgreSQL/SQLite)                       │
└─────────────────────────────────────────────────────── ┘
```

---

## 4. Frontend — Detailed Design

### 4.1 Tech Stack
| Layer | Technology | Why |
|-------|-----------|-----|
| Map | Mapbox GL JS / Leaflet | Smooth zoom, custom markers, WebGL performance |
| Framework | React (Vite) | Fast dev, component model, hackathon-friendly |
| Styling | Tailwind CSS | Rapid styling, consistent design |
| Animations | Framer Motion | Smooth hover/transition animations |
| Charts | Recharts or Chart.js | Dashboard stats |
| State | React Query (TanStack) | Server state caching, auto-refresh |

### 4.2 Map View (Main Screen)
- **Pothole markers:** Color-coded dots on the map
  - 🔴 Open > 30 days (critical)
  - 🟡 Open 14–30 days (warning)
  - 🟢 Open < 14 days (recent)
  - ⚪ Closed (faded/dimmed, toggleable)
- **Hover tooltip** (smooth fade-in animation):
  - Pothole ID / complaint number
  - Date opened → days open
  - Estimated size (if available from descriptor)
  - Accident count near this pothole
  - Daily vehicles affected (traffic volume)
  - ML-predicted: "Repair ETA: ~X days" / "Accident risk: HIGH"
- **Click → Detail panel** slides in from right:
  - Full complaint details
  - Nearby collisions list
  - ML prediction breakdown
  - "Report/escalate" button

### 4.3 Dashboard (Secondary View)
- Borough-level summary cards (total open, avg days open, accident count)
- Time-series chart: potholes opened vs. closed per week
- Top 10 worst potholes by impact score
- Alert history log

### 4.4 Animation & UX Principles
- Map markers appear with scale-in animation on load
- Hover transitions: 150ms ease-out
- Panel slides: 300ms spring animation
- Color transitions on status change: smooth 200ms
- Loading states: skeleton placeholders, not spinners
- Mobile-responsive: map takes full screen, panels overlay on mobile

---

## 5. Backend — Detailed Design

### 5.1 Tech Stack
| Component | Technology | Why |
|-----------|-----------|-----|
| API Framework | FastAPI (Python) | Async, auto-docs, ML-friendly ecosystem |
| Database | SQLite (hackathon) / PostgreSQL (production) | Quick setup, geospatial with PostGIS |
| Task Queue | Celery + Redis (or background tasks) | Scheduled data refresh |
| ML Runtime | scikit-learn / XGBoost | Fast training, good enough for hackathon |

### 5.2 API Endpoints

```
GET  /api/potholes                    — List all open potholes (with lat/lng, status, days_open)
GET  /api/potholes/{id}               — Single pothole detail + ML predictions
GET  /api/potholes?borough=...        — Filter by borough
GET  /api/potholes?status=open|closed — Filter by status

GET  /api/stats/summary               — Borough-level aggregated stats
GET  /api/stats/timeline              — Time-series data (opened vs closed per week)

POST /api/alerts/send                 — Trigger DOT notification for a pothole
GET  /api/alerts/history              — List of sent alerts and their status

GET  /api/predictions/{pothole_id}    — Get ML prediction (repair ETA, accident risk)
```

### 5.3 Data Ingestion Pipeline

```
Scheduled Job (every 6 hours):
  1. Fetch new 311 pothole complaints since last pull
     → SODA API: $where=descriptor='Pothole' AND created_date > '{last_pull}'
  2. Fetch recent collision data
     → SODA API: crash_date > '{last_pull}'
  3. Geospatial join collisions ↔ potholes
     → Within 25m radius, during open period
  4. Join traffic volume data
     → Match pothole street segment to AADT data
  5. Run ML predictions on new/updated potholes
  6. Check alert thresholds → queue notifications if needed
  7. Store enriched records in database
```

### 5.4 Database Schema

```sql
CREATE TABLE potholes (
    id              TEXT PRIMARY KEY,       -- 311 unique_key
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    borough         TEXT,
    zip_code        TEXT,
    descriptor      TEXT,
    status          TEXT,                   -- 'open' or 'closed'
    created_date    DATETIME NOT NULL,
    closed_date     DATETIME,
    days_open       INTEGER,               -- computed
    street_segment  TEXT,                  -- for traffic join
    impact_score    REAL                   -- computed ML output
);

CREATE TABLE collisions (
    id              TEXT PRIMARY KEY,       -- collision_id
    crash_date      DATETIME,
    latitude        REAL,
    longitude       REAL,
    persons_injured INTEGER,
    persons_killed  INTEGER,
    contributing_factor TEXT
);

CREATE TABLE pothole_collisions (
    pothole_id      TEXT REFERENCES potholes(id),
    collision_id    TEXT REFERENCES collisions(id),
    distance_m      REAL,                   -- distance in meters
    PRIMARY KEY (pothole_id, collision_id)
);

CREATE TABLE alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pothole_id      TEXT REFERENCES potholes(id),
    sent_date       DATETIME,
    status          TEXT,                   -- 'sent', 'acknowledged', 'failed'
    message         TEXT
);
```

---

## 6. Machine Learning — Detailed Design

### 6.1 Model 1: Accident Risk Prediction (Classification)

**Goal:** Predict the likelihood of an accident occurring near a given pothole.

| Aspect | Detail |
|--------|--------|
| Target | Binary: `has_nearby_accident` (1 if collision within 25m while pothole was open) |
| Features | See below |
| Model | XGBoost classifier (handles tabular data well, fast to train) |
| Output | Probability score 0–1; binned into LOW / MEDIUM / HIGH risk |

**Features:**
```
- days_open              — how long the pothole has been active
- borough_encoded        — one-hot encoded borough
- traffic_volume_aadt    — average daily traffic on this street
- nearby_pothole_count   — other potholes within 100m
- month                  — seasonal effect (winter = more potholes + worse conditions)
- day_of_week            — weekday vs weekend traffic patterns
- latitude / longitude   — spatial signal
- zip_code_encoded       — neighborhood-level patterns
```

**Training data construction:**
- Positive class: potholes that had ≥1 collision within 25m while open
- Negative class: potholes with no nearby collisions
- Balance with SMOTE or class weighting if imbalanced

### 6.2 Model 2: Repair Timeline Prediction (Regression)

**Goal:** Predict how many days until a pothole will be closed, given current features.

| Aspect | Detail |
|--------|--------|
| Target | `days_to_close` = closed_date - created_date (only for closed potholes) |
| Model | XGBoost regressor |
| Output | Predicted days until repair; for open potholes, estimated remaining days |

**Features:**
```
- days_open              — current age of the pothole
- borough_encoded        — some boroughs fix faster
- traffic_volume_aadt    — high-traffic may get priority
- nearby_pothole_count   — cluster effect (batch repairs?)
- month                  — seasonal repair capacity
- has_nearby_accident    — binary flag (accidents may accelerate repair)
- complaint_count        — number of 311 complaints for this pothole
```

### 6.3 Model 3: Impact Score (Composite Ranking)

**Goal:** Single priority number to rank which potholes need attention most.

```
impact_score = (
    0.3 * accident_risk_probability +
    0.25 * normalized_traffic_volume +
    0.25 * normalized_days_open +
    0.2 * nearby_accident_count_normalized
)
```

This feeds directly into the alert system — potholes above a threshold auto-notify DOT.

### 6.4 ML Pipeline
```
Raw data → Feature engineering → Train/Val split (80/20)
  → XGBoost training → Hyperparameter tuning (GridSearchCV)
  → Evaluate (ROC-AUC for classifier, RMSE for regressor)
  → Serialize with joblib → Serve via FastAPI endpoint
```

### 6.5 Hackathon Simplifications
- Use last 2 years of data (not full 14-year dataset) to keep training fast
- Skip hyperparameter tuning — use sensible defaults
- Pre-compute features nightly instead of real-time
- Use SQLite instead of PostGIS for MVP

---

## 7. Alert System — Automated DOT Notification

### 7.1 How It Works
```
Every 6 hours (or on data refresh):
  1. Recalculate impact_score for all open potholes
  2. Filter: impact_score > THRESHOLD (e.g., top 5%)
  3. For each high-impact pothole:
     a. Generate alert message with data:
        - Pothole location + map link
        - Days open
        - Daily vehicles affected
        - Accident risk level + nearby collision count
        - ML-predicted repair timeline
     b. Send via NYC 311 API (or email fallback)
     c. Log alert in database
```

### 7.2 NYC 311 API Integration
- **Option A (Preferred):** [NYC 311 OpenAPI](https://api-311.data.cityofnewyork.us/) — programmatically submit service requests
- **Option B:** Email alerts to DOT borough offices (each borough has a dedicated email)
- **Option C (hackathon MVP):** Generate alert JSON/email draft and display in dashboard — prove the concept without hitting a real API

### 7.3 Alert Message Template
```
Subject: [PotholeTracker] High-Impact Pothole Alert — {borough}

Location: {address} ({lat}, {lng})
Days Open: {days_open}
Daily Vehicles Affected: ~{traffic_volume}
Nearby Accidents: {collision_count}
Accident Risk: {risk_level} ({risk_probability}%)
Predicted Repair Time: {predicted_days} days

This pothole has been automatically flagged based on impact analysis.
Please prioritize inspection and repair.
```

---

## 8. Implementation Plan — Hackathon Timeline

### Phase 1: Foundation (Hours 0–4)
| # | Task | Owner | Output |
|---|------|-------|--------|
| 1.1 | Set up project repo (React + FastAPI) | — | Running hello-world |
| 1.2 | Fetch & cache 311 pothole data | Backend | `data/potholes.csv` |
| 1.3 | Fetch & cache collision data | Backend | `data/collisions.csv` |
| 1.4 | Set up SQLite DB + schema | Backend | `potholes.db` |
| 1.5 | Build basic ETL script | Backend | `etl.py` populating DB |
| 1.6 | Scaffold React app with Mapbox | Frontend | Map rendering NYC |

### Phase 2: Core Features (Hours 4–10)
| # | Task | Owner | Output |
|---|------|-------|--------|
| 2.1 | GET /api/potholes endpoint | Backend | API returning pothole data |
| 2.2 | Map markers with color coding | Frontend | Dots on map |
| 2.3 | Hover tooltip with pothole info | Frontend | Tooltip showing days open |
| 2.4 | Geospatial join (potholes ↔ collisions) | Backend | `pothole_collisions` table |
| 2.5 | Traffic volume join | Backend | `traffic_volume_aadt` in potholes |
| 2.6 | Dashboard stats endpoint | Backend | GET /api/stats/summary |

### Phase 3: ML & Intelligence (Hours 10–16)
| # | Task | Owner | Output |
|---|------|-------|--------|
| 3.1 | Feature engineering script | ML | `features.csv` |
| 3.2 | Train accident risk model | ML | `model_accident_risk.pkl` |
| 3.3 | Train repair timeline model | ML | `model_repair_timeline.pkl` |
| 3.4 | Compute impact scores | ML | `impact_score` column in DB |
| 3.5 | GET /api/predictions/{id} endpoint | Backend | ML predictions via API |
| 3.6 | Display predictions in tooltip/panel | Frontend | Risk level, repair ETA |

### Phase 4: Alert System & Polish (Hours 16–24)
| # | Task | Owner | Output |
|---|------|-------|--------|
| 4.1 | Alert threshold logic | Backend | Auto-flagging high-impact potholes |
| 4.2 | Alert generation (email draft or API) | Backend | POST /api/alerts/send |
| 4.3 | Alert history in dashboard | Frontend | Alert status panel |
| 4.4 | Animations & polish | Frontend | Framer Motion transitions |
| 4.5 | Mobile responsiveness | Frontend | Works on phone |
| 4.6 | Demo prep & README | All | Recorded demo |

---

## 9. Tech Stack Summary

```
Frontend:  React + Vite + TypeScript + Mapbox GL JS + Tailwind + Framer Motion
Backend:   FastAPI + SQLite + GeoJSON
ML:        Python + scikit-learn + XGBoost + pandas
Data:      NYC Open Data (311, Collisions, Traffic) via SODA API
Alerts:    NYC 311 API / Email (SMTP) / Dashboard display
Deploy:    Vercel (frontend) + Railway/Render (backend)
```

---

## 10. Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| 311 API rate limits or downtime | Cache all data locally at start; work from cache |
| Geospatial join too slow on full dataset | Limit to last 2 years; use bounding box filters |
| ML model poor accuracy | Use simple heuristics as fallback; XGBoost is robust on tabular data |
| No real 311 API access for alerts | Generate alert drafts in dashboard; prove the concept |
| Mapbox API key required | Use free tier (50k loads/mo) or fall back to Leaflet + OpenStreetMap |
| Time pressure (hackathon) | Cut traffic volume join first; use borough averages as proxy |

---

## 11. Key API Queries (Starter)

```bash
# Fetch last 2 years of pothole complaints
curl "https://data.cityofnewyork.us/resource/erm2-nwe9.json?\$where=descriptor='Pothole'%20and%20created_date%20%3E%20'2024-01-01T00:00:00'&\$limit=50000"

# Fetch collisions near a specific location (example: Manhattan)
curl "https://data.cityofnewyork.us/resource/h9gi-nx95.json?\$where=latitude%20IS%20NOT%20NULL%20and%20crash_date%20%3E%20'2024-01-01'&\$limit=50000"

# Traffic volume counts
curl "https://data.cityofnewyork.us/resource/bf4a-6vgj.json?\$limit=50000"
```