# PotholeIQ — Demo Script (5 minutes)

**HunterHack 2026 · Hunter College · April 25, 2026**
**Team: Taskin (Frontend), Kevin (Backend + ML), Kazi, Rakhmonjon**

---

## 1. Problem Statement (30 sec)

> "NYC gets over 200,000 pothole complaints a year. The city logs them — but has no data-driven way to know which ones to fix first. Meanwhile, drivers hit dangerous potholes that have been sitting open for months.
> PotholeIQ changes that."

---

## 2. Map Demo (90 sec)

- Open the app → show the map with colored dots across all 5 boroughs
- Point out the color coding:
  - **Red** = Critical / High risk (open, dangerous)
  - **Orange** = Medium risk
  - **Green** = Fixed / Closed
- Zoom into Manhattan → show dense cluster near Harlem River Drive
- **Hover** over a red dot → tooltip appears:
  - *"Open 23 days · HARLEM RIVER DRIVE, Manhattan"*
  - *"Risk Score: 51.8 / 100 · 10 crashes nearby"*
  - *"16,591 vehicles/day · AADT: 97,246/year"*
- **Click** the dot → detail panel opens:
  - *"Accident Risk: HIGH (51.8% probability)"*
  - *"Estimated repair: 9 days"*
  - *"Nearby crashes: 10 within 200m"*
  - *"Pavement-specific crash: YES within 500m"*

---

## 3. Dashboard (60 sec)

- Switch to Dashboard view
- Show the summary cards:
  - **3,936** total potholes tracked
  - **792** currently open
  - **2,899** closed
  - **12.2 days** average time open
- Show borough breakdown:
  - Manhattan: 248 open, avg 13.9 days, 14,368 nearby crashes
  - Queens: 62 open but 18,987 nearby crashes (high traffic)
- Show the weekly timeline chart:
  - Week 13: 1,078 opened vs 535 closed → backlog growing
  - Week 15: 1,065 opened vs 1,103 closed → city catching up

---

## 4. Alert System (60 sec)

- Go back to the high-risk pothole on Harlem River Drive
- Click **"Alert DOT Department"**
- Show the generated alert:

  ```
  [PotholeIQ] HIGH Risk — HARLEM RIVER DRIVE, MANHATTAN
  Pothole ID  : 68538157
  Days Open   : 23 days
  Risk Score  : 51.8 / 100
  Daily Volume: 16,591 vehicles/day
  Nearby Crashes: 10 within 200m
  Pavement Crash: YES within 500m
  Est. Fix Days : 9
  ```

- *"This fires automatically to the NYC DOT with everything they need to act — location, traffic exposure, crash history, and urgency score."*

---

## 5. Technical Highlights (60 sec)

- **Data:** 4 live NYC Open Data sources — 311 complaints, traffic counts, AADT, NYPD collisions
- **ML:** Two XGBoost models — risk regressor (RMSE 2.77) + urgency classifier (ROC-AUC 0.96)
- **Embeddings:** 384-dim sentence embeddings on every pothole for semantic search
- **Backend:** FastAPI + SQLite + GeoJSON — 16 endpoints, rate-limited, CORS-secured
- **Stack:** React + Leaflet/Mapbox · Python + FastAPI · XGBoost + joblib

---

## 6. Closing (30 sec)

> "Every pothole has a story — how long it's been open, how many cars pass over it, how many crashes happened nearby. PotholeIQ reads that story and tells the city which ones need fixing today.
> Thank you."

---

## Backup Talking Points (if questions come up)

**"How accurate is the ML?"**
> Risk score RMSE of 2.77 points on a 0–100 scale. Urgency classifier ROC-AUC of 0.959.

**"What if the API is down?"**
> We cache all data in SQLite locally — the map and predictions work offline.

**"How does it know traffic volume?"**
> We join NYC DOT Automated Traffic Recorder data by street name, with NY State AADT as a secondary source. 99.9% of potholes get a real traffic count.

**"Could this scale to other cities?"**
> Yes — the pipeline only needs a 311-style complaint API and a traffic dataset. Any city with open data works.
