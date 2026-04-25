# PotholeIQ

**NYC Pothole Risk Intelligence Map**

> Real-time pothole tracking, ML-powered risk scoring, and automated alerts to the NYC Department of Transportation.

---

## Overview

Every day, thousands of NYC drivers encounter potholes that have been sitting open for weeks or months. The city logs them — but doesn't always know which ones to prioritize. PotholeIQ changes that.

We pull live pothole data from NYC Open Data, visualize every report on an interactive map, and use machine learning to score each pothole's accident risk and repair urgency. When a pothole crosses a danger threshold, the app automatically fires an alert to the relevant DOT or sanitation department — with everything they need to act fast.

---

## Features

### Map Visualization
- One dot per pothole — no heatmaps, full granularity
- Color-coded by status: **red** (open) vs **green** (fixed)
- Hover tooltip showing:
  - How long the pothole has been open
  - Pothole size and type
  - Estimated daily cars affected
  - Related accident reports (if available)
  - ML risk score and urgency tier
- Smooth animations and a clean, usable UI

### ML Risk Engine
- **Accident prediction** — probability this pothole causes an accident before it's fixed
- **Fix priority prediction** — urgency tier and estimated fix date
- Inputs: pothole age, size, traffic volume, location
- Outputs: risk score (0–100), urgency tier (Low / Medium / High / Critical), predicted fix date

### Auto-Alert System
- App polls NYC Open Data on a set interval
- Flags potholes crossing danger thresholds (age, traffic, risk score)
- Sends automated alerts to local DOT/sanitation with:
  - Pothole location and how long it's been open
  - Daily estimated cars impacted
  - Predicted accident risk score
- Alert format: email or API push (TBD)

---

## Data Sources

| Source | Data |
|--------|------|
| [NYC Open Data — 311 Service Requests](https://data.cityofnewyork.us/) | Pothole reports: location, status, date opened/closed, size, type |
| NYC DOT / Traffic Data | Traffic volume per street segment |
| NYPD Collision Data (TBD) | Accident reports near pothole locations |

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | React, Mapbox GL JS / Leaflet |
| Backend | Python (FastAPI) |
| ML | scikit-learn / XGBoost |
| Data | NYC Open Data API |
| Alerts | Email (SMTP) / REST API push |

---

## Team

| Name | Role |
|------|------|
| Taskin | Frontend — Map, UI, dashboard, animations |
| Kevin | Backend + ML — API, XGBoost pipeline, data, alerts |
| Kazi | Data + Polish — Testing, demo prep, deployment |
| Rakhmonjon | Full-stack + Security — CORS, validation, integration |

**HunterHack 2026** — Hunter College Hackathon, April 25, 2026

---

## Open Questions

- Does NYC Open Data include accident cost data?
- Where does reroute / traffic volume data come from?
- How is the alert delivered to the sanitation department?
- ML model approach: regression (risk score) or classification (urgency tier) — or both?

---

## Getting Started

```bash
# Clone the repo
git clone https://github.com/Taskinr-afk/HunterHack.git
cd HunterHack
```

Setup instructions per module will be added as the project is built out.

---

## License

MIT
