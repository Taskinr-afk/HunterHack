# Taskin + Kevin Split Tasks

## Purpose
This file tracks the current frontend prototype handoff from Taskin's local `Front-end` workspace into the shared `HunterHack/Taskin/Front-end` folder, plus the backend integration items Kevin will plug in later.

## Ownership Split

### Taskin
- Owns all UI work under `Taskin/Front-end/`
- Owns map/list browsing experience, motion, filters, mobile layout, and dashboard presentation
- Owns mock-data fallback until backend merge
- Owns keeping the frontend tree merge-safe:
  - `public/`
  - `src/api/`
  - `src/components/`
  - `src/hooks/`
  - `src/pages/`
  - `src/types/`
  - `src/utils/`
  - `src/App.tsx`
  - `src/main.tsx`
  - `src/index.css`
  - `.env.example`
  - `package.json`
  - `tailwind.config.ts`
  - `tsconfig.json`
  - `vite.config.ts`

### Kevin
- Owns FastAPI routes and real data contract
- Owns live data availability for:
  - `GET /stats`
  - `GET /potholes/geojson`
  - `GET /potholes/{unique_key}`
  - `POST /predict`
  - `POST /alerts/send`
  - `POST /admin/refresh`
- Owns final response shapes for borough, zip, address, coordinates, traffic, collisions, risk, urgency, and repair ETA
- Owns backend performance once the mock dataset is replaced

## Current Frontend State
- The app is currently frontend-complete enough for demos without Kevin's backend.
- Main page is now mock-driven, geolocation-first, and Zillow-style:
  - split list + map layout
  - nearest pothole sorting
  - viewport-aware browsing
  - address, zip code, city, borough, and status filters
  - animated detail panel
- Dashboard route is also mock-driven so it is no longer blank while backend work is in progress.

## File-by-File Change Log

### Root files
- `Taskin/Front-end/.env.example`
  - Added `VITE_API_BASE_URL` template for future backend hookup.
- `Taskin/Front-end/index.html`
  - Updated Vite entry to `src/main.tsx`.
- `Taskin/Front-end/package.json`
  - Added TypeScript and React type dependencies needed for the TS migration.
- `Taskin/Front-end/package-lock.json`
  - Updated lockfile for the installed frontend dependency set.
- `Taskin/Front-end/tailwind.config.ts`
  - Added config file so the expected frontend tree is present.
- `Taskin/Front-end/tsconfig.json`
  - Added strict TypeScript config for the frontend app.
- `Taskin/Front-end/vite.config.ts`
  - Added Vite TypeScript config.

### Public files
- `Taskin/Front-end/public/.gitkeep`
  - Keeps the required `public/` directory in source control.
- `Taskin/Front-end/public/frontend-change-notes.md`
  - Added downloadable frontend-only notes for the current implementation pass.

### App shell
- `Taskin/Front-end/src/App.tsx`
  - Replaced the old scene-switcher with route-based app navigation.
- `Taskin/Front-end/src/main.tsx`
  - Added React Query provider and TypeScript entrypoint.
- `Taskin/Front-end/src/index.css`
  - Rebuilt the visual system for the new animated Zillow-style browsing layout.

### API layer
- `Taskin/Front-end/src/api/client.ts`
  - Keeps shared fetch wrapper for future backend reintegration.
- `Taskin/Front-end/src/api/potholes.ts`
  - Keeps pothole endpoint helpers and query builder for Kevin merge.
- `Taskin/Front-end/src/api/stats.ts`
  - Keeps stats endpoint helper for Kevin merge.
- `Taskin/Front-end/src/api/alerts.ts`
  - Keeps alert and refresh endpoint helpers for Kevin merge.

### Components
- `Taskin/Front-end/src/components/AppShell.tsx`
  - Added shared top nav shell for map and dashboard routes.
- `Taskin/Front-end/src/components/ErrorMessage.tsx`
  - Keeps reusable error state component.
- `Taskin/Front-end/src/components/LoadingSpinner.tsx`
  - Keeps reusable loading state component.
- `Taskin/Front-end/src/components/MapFilters.tsx`
  - Reworked filters for address, zip code, city, borough, and status.
- `Taskin/Front-end/src/components/PotholeMap.tsx`
  - Reworked map into a Zillow-style browsing panel with animated focus and nearby markers.
- `Taskin/Front-end/src/components/PotholeDetail.tsx`
  - Reworked detail panel to run from local mock data with animated risk, metrics, and mock alert flow.

### Hooks
- `Taskin/Front-end/src/hooks/useViewportPotholes.ts`
  - Kept bounds tracking for map viewport sync.
- `Taskin/Front-end/src/hooks/useUserLocation.ts`
  - Added browser geolocation hook for location-first browsing.

### Pages
- `Taskin/Front-end/src/pages/MapPage.tsx`
  - Rebuilt the main page into a split list/map explorer driven by mock data.
- `Taskin/Front-end/src/pages/Dashboard.tsx`
  - Rebuilt the dashboard to use mock summary, borough, and timeline data so it remains demo-ready.

### Types
- `Taskin/Front-end/src/types/index.ts`
  - Expanded types for address, city, zip, user location, and the TypeScript migration.

### Utils
- `Taskin/Front-end/src/utils/map.ts`
  - Added distance, formatting, filter matching, and map helper logic for client-side browsing.
- `Taskin/Front-end/src/utils/mockData.ts`
  - Added arbitrary pothole dataset plus mock stats and timeline builders.

## Kevin Merge Checklist
- Replace `mockPotholes` and `buildMockStatsResponse()` with real API-backed query hooks.
- Confirm backend returns:
  - `latitude`
  - `longitude`
  - `borough`
  - `city`
  - `zip_code`
  - `address` or enough street fields to compose it
  - `status`
  - `days_open`
  - `risk_score`
  - `nearby_collision_count`
  - `traffic_volume`
  - `accident_risk`
  - `accident_risk_probability`
  - `predicted_repair_days`
  - `repair_eta`
  - `created_date`
  - `closed_date`
  - `urgency_tier`
- Confirm `/stats` returns:
  - totals
  - borough breakdown
  - weekly timeline or a second route for timeline
- Replace mock alert mutation in `PotholeDetail.tsx` with the real `POST /alerts/send` path once ready.

## Merge Notes
- The current frontend tree is intentionally strict to avoid Taskin-side merge conflicts.
- Backend integration should prefer adapting the hook/query layer first, not reshaping the UI tree.
