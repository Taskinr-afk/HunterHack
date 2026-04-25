# PotholeIQ — Frontend Features Breakdown

_What exists in the local preview build vs. what the full plan requires._

---

## What Is Currently Built (Local Preview)

### 1. Variation Switcher
- Three design modes switchable at runtime: Night City, Civic Pro, Alert Dash
- Animated active pill indicator using Framer Motion `layoutId`
- Fade + slide transition between modes using `AnimatePresence`

---

### 2. Mock Map (SVG — no real data, no API key needed)
- 6 horizontal streets + 9 vertical avenues rendered as a grid
- 25 hardcoded pothole data points, each with:
  - X/Y position on the grid
  - Risk level: critical / high / medium / low
  - Open or closed status
  - Age in days
  - Cars per day
  - Street name label
- Dot color codes by risk level
- Closed potholes rendered as faded
- Critical open potholes have an animated pulse ring (Framer Motion)
- Hover over any dot shows a tooltip with: street name, risk level, status, days open, cars/day
- Dots scale up on hover
- Three swappable color themes: dark / light / amber
- Legend in bottom-left corner

---

### 3. Night City Variation
- Header: logo, project name, monospace label, live pulse dot
- Hero title with glowing red text-shadow
- 4 stat cards: open potholes, fixed this week, critical risk, avg days open
- Live alert feed panel with 4 alerts (location + severity badge)
- Active alert cycles highlight every 3 seconds via `setInterval`
- "Send DOT Alert" CTA button
- 2-column layout: map (2/3) + alert panel (1/3)

---

### 4. Civic Pro Variation
- White header with NYC blue branding and orange "Alert DOT" button
- 4 stat cards with emoji icon + colored badge chip
- Priority queue table: 6 potholes sorted by risk score (0-100)
- Each row shows: street name, borough, days open, risk score
- Rows are clickable and highlight on selection
- 3/5 map + 2/5 table layout
- "Send DOT Alert for Top 5" button at the bottom of the table

---

### 5. Alert Dash Variation
- Icon-only 56px sidebar with 5 navigation icons, amber active state
- Top stats strip with 5 compact metrics
- Alert queue panel using `AnimatePresence`: new alert slides in from the right after 2.2 seconds
- Borough breakdown section with 5 boroughs
- Each borough shows count + animated progress bar (Framer Motion, `easeOut`)
- "Dispatch DOT Alert" button

---

## What the Full Plan Requires (from 02_FRONTEND_PLAN.md)

### Pages
- Map page (main view)
- Dashboard page (stats + charts)
- React Router for navigation between pages

### Real Map
- Leaflet (`react-leaflet`) with OpenStreetMap tiles
- Real NYC coordinates from the backend API
- Circle markers colored by days open (green < 14 days, amber 14-30, red > 30)
- Tooltip on hover
- Click marker to open detail panel

### Pothole Detail Panel
- Slides in from the right (Framer Motion spring)
- Shows: status badge, days open, borough, accident risk level, nearby collision count, daily vehicle count, repair ETA
- ML Predictions section: risk probability (e.g. "High Risk — 83.2%"), repair estimate
- "Alert DOT Department" button triggers POST to backend
- Shows created/closed dates

### Filters
- Borough dropdown (All / Manhattan / Brooklyn / Queens / Bronx / Staten Island)
- Status dropdown (All / Open Only / Closed Only)
- Filters update the map in real time

### API Layer
- Centralized fetch client pointing to `VITE_API_BASE_URL`
- `GET /potholes/geojson` with params (status, borough, min_risk, urgency, limit)
- `GET /potholes/{unique_key}` for detail + ML predictions
- `GET /stats` for summary + per-borough breakdown
- `POST /predict` for live risk scoring
- `POST /admin/refresh` to re-fetch + re-score

### Data Fetching
- React Query for caching, loading state, error state, auto-retry
- 5-minute stale time
- No refetch on window focus

### Dashboard Page
- 4 summary cards: total open, total closed, avg days open, boroughs tracked
- Borough breakdown: bar showing open vs closed count per borough
- Weekly timeline chart: bars for "potholes opened" vs "potholes closed" per week (Recharts)

### Loading + Error States
- Loading spinner component while API fetches
- Error message component with retry button
- Applied to both the map page and dashboard

### Mobile Responsive
- Detail panel goes full-width on small screens (vs 384px on desktop)
- Filter bar stacks vertically on mobile
- Dashboard cards stack to single column on mobile

---

## Gap Summary

| Feature | Built (Preview) | Needed (Full) |
|---|---|---|
| Map | SVG mock, no real coords | Leaflet with real NYC data |
| Pothole data | 25 hardcoded | Live from backend API |
| Detail panel | Not built | Slide-in with ML predictions |
| Filters | Not built | Borough + status dropdowns |
| Dashboard page | Not built | Charts, stats, borough bars |
| Routing | Not built | React Router (Map + Dashboard) |
| API integration | Not built | React Query + fetch client |
| Loading states | Not built | Spinner + error + retry |
| Mobile layout | Not tested | Responsive breakpoints |
| TypeScript | Not used (JSX only) | Full TypeScript (TSX) |

---

## Shared Placeholder Data (Used in Preview)

- Open potholes: 4,821
- Fixed this week: 312
- Critical risk: 47
- Avg days open: 38
- Brooklyn: 1,432 | Queens: 1,204 | Bronx: 987 | Manhattan: 743 | Staten Island: 455
- Alert examples: Atlantic Ave Brooklyn, 125th St Manhattan, Queens Blvd, 3rd Ave Bronx
