# Frontend Change Notes

## Summary
- Kept the `Front-end` file tree contract intact:
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
- Removed the old `src/scenes/` and `src/variations/` folders.

## Main Page
- Reworked the home page into a Zillow-style split layout:
  - results/list panel
  - sticky map panel
  - filters for address, zip code, city, borough, and status
  - client-side nearest-pothole sorting
  - map/list sync based on viewport
- Added geolocation prompt on load and a recenter flow.
- Switched the page to mock pothole data so it works without Kevin's backend.

## Map Behavior
- Added client-side mock pothole records with addresses, zip codes, coordinates, risk, and status.
- Added viewport-aware nearby browsing so moving the map changes which potholes are featured.
- Added animated UI treatments and motion-driven cards/panels.

## Dashboard
- Replaced the empty dashboard state with mock summary metrics, borough breakdown, and weekly activity data.

## Future Merge Notes
- `src/api/*` is still present for Kevin's backend integration later.
- The current UI uses mock data from `src/utils/mockData.ts`.
- When the backend is ready, the app can swap from local mock sources back to API-backed hooks without changing the folder structure.
