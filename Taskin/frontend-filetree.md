# PotholeIQ — Frontend File Tree

_Last updated: 2026-04-25_

```
potholeiq-frontend/
├── index.html                          ← Vite entry; includes Leaflet CSS CDN link
├── package.json                        ← deps: react, vite, framer-motion, leaflet,
│                                         react-leaflet, @tanstack/react-query, recharts
│
└── src/
    ├── main.jsx                        ← Vite mount point; wraps App
    ├── App.jsx                         ← Root: QueryClient provider, scene state
    │                                     (hero | overview | mission-control),
    │                                     AnimatePresence blur+scale transitions
    │
    ├── scenes/
    │   └── Hero.jsx                    ← Cinematic landing: 4-layer mouse parallax,
    │                                     spring physics, ambient drift dots, scanline,
    │                                     animated counters, CTA → overview
    │
    ├── variations/
    │   ├── NightCity.jsx               ← Overview scene: dark #080810 bg, red accents,
    │   │                                 live stats from API, 2/3 map + 1/3 alert feed,
    │   │                                 cycling highlight every 3s, "Mission Control →"
    │   └── AlertDash.jsx               ← Mission control: slate bg, amber accents,
    │                                     icon sidebar (🏠 returns to overview),
    │                                     top stats strip, map + alert queue + borough bars,
    │                                     new alert animates in at 2.2s, Dashboard tab
    │
    ├── pages/
    │   └── Dashboard.jsx               ← Stats deep-dive: 4 stat cards, borough progress
    │                                     bars, Recharts BarChart for weekly timeline
    │
    ├── components/
    │   ├── PotholeMap.jsx              ← Leaflet map (CARTO dark tiles), viewport-based
    │   │                                 loading via useViewportPotholes, CircleMarker
    │   │                                 per pothole, falls back to MockMap on API error
    │   ├── PotholeDetail.jsx           ← Spring slide-in panel: risk score bar, ML
    │   │                                 predictions, accident risk, send alert mutation
    │   ├── MapFilters.jsx              ← Floating overlay: borough / status / min_risk
    │   │                                 selects, dark/light mode, updates parent state
    │   ├── MockMap.jsx                 ← SVG fallback map when API is offline,
    │   │                                 shows "DEMO MODE — API OFFLINE" badge
    │   ├── LoadingSpinner.jsx          ← Rotating border-top spinner, monospace message
    │   └── ErrorMessage.jsx            ← Warning + message + optional RETRY button
    │
    ├── hooks/
    │   └── useViewportPotholes.js      ← Zillow-style viewport loading: useMapEvents
    │                                     listens for moveend/zoomend, debounces 400ms,
    │                                     passes lat_min/max lng_min/max to API.
    │                                     Exports: useViewportPotholes(), BoundsTracker
    │
    ├── api/
    │   ├── client.js                   ← Base fetchAPI: reads VITE_API_BASE_URL,
    │   │                                 throws on non-OK, returns JSON
    │   ├── potholes.js                 ← getPotholesGeoJSON(params) → /potholes/geojson
    │   │                                 (supports bbox + status/borough/risk filters),
    │   │                                 getPotholeById(key), predictPothole(data)
    │   ├── stats.js                    ← getStats() → /stats
    │   └── alerts.js                   ← sendAlert(id) → /alerts/send,
    │                                     adminRefresh(secret) → /admin/refresh
    │
    └── utils/
        └── map.js                      ← markerColor(feature): closed=green, risk>70=red,
                                          risk>40=amber | markerRadius(f, selected)
                                          urgencyLabel(tier) | fmtDays(days) | riskColor(score)
```

---

## API Endpoint Note

Frontend uses endpoints from `claude.md` (the team's live working spec):

| Action | Endpoint |
|---|---|
| Load pothole map data | `GET /potholes/geojson` |
| Load stats/summary | `GET /stats` |
| Get single pothole | `GET /potholes/{unique_key}` |
| Send DOT alert | `POST /alerts/send` |
| ML predict | `POST /predict` |

**Bbox params** (needed for viewport loading): `lat_min`, `lat_max`, `lng_min`, `lng_max`  
Kevin / Rakhmon: the frontend will send these as query params to `/potholes/geojson`. The FastAPI route needs to filter by these if present.

---

## Scene Flow

```
Hero  ──[Enter]──▶  NightCity (overview)  ──[Mission Control →]──▶  AlertDash
                         ▲                                               │
                         └──────────────────[🏠 home]────────────────────┘
```