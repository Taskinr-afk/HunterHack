# PotholeIQ Full-Stack Review Report

**Date:** 2026-04-26  
**Scope:** MainProject/ (Backend + Frontend), configuration, deployment, security  
**Test Results:** Backend 30/30 passing, Frontend build succeeds  

---

## CRITICAL — Must Fix Before Demo

### C1. SMTP env var mismatch — emails will never send
**File:** `Backend/.env` line 7 vs `Backend/app/services/alert_service.py` line 18  
`.env` uses `SMTP_PASSWORD=` but the code reads `os.getenv("SMTP_PASS", "")`.  
Different variable names = SMTP auth silently fails every time.  
**Fix:** Change `.env` to `SMTP_PASS=` (matching `.env.example`), or change the code.

### C2. Admin API key and secret exposed in client bundle
**File:** `Frontend/src/api/alerts.ts` lines 4, 20-23  
`VITE_` prefixed env vars are inlined into the production JS bundle at build time. Anyone who opens dev tools can extract the admin API key. The `adminRefresh` function hardcodes `secret="potholeiq-dev"` as a query parameter, which also appears in browser history and server logs.  
**Fix:** Move admin operations to a server-side route or use a backend proxy. Remove `VITE_ADMIN_API_KEY` from the frontend entirely. Admin refresh should use server-side auth, not a client-side secret.

### C3. `/potholes/{unique_key}` returns raw database row without schema validation
**File:** `Backend/app/main.py` line 212-221  
`return dict(row)` leaks internal fields (`zip_code`, `location_type`, `pavement_crash_nearby`) and returns unvalidated data. The proper endpoint `/api/potholes/{pothole_id}` returns a `PotholeDetailResponse` with ML predictions. This creates inconsistent API contracts.  
**Fix:** Replace with proper schema validation or remove this route (the `/api/` version is the canonical one).

### C4. Duplicate alert routers with different implementations
**Files:** `Backend/app/alerts.py` (prefix `/alerts`) and `Backend/app/api/alerts_api.py` (prefix `/api/alerts`)  
Both are registered in `main.py` (lines 118, 122). This creates:
- `POST /alerts/send` — query param `pothole_id` (alerts.py)
- `POST /api/alerts/send` — JSON body `AlertRequest` (alerts_api.py)
- `GET /alerts/history` vs `GET /api/alerts/history`  
Different auth, different schemas, different response shapes for essentially the same operations.  
**Fix:** Remove `alerts.py` router and keep only `alerts_api.py` (the `/api/` version). Update any frontend calls that use the old routes.

### C5. `risk_score` format crash when value is `None`
**Files:** `Backend/app/alerts.py` line 70, `Backend/app/services/alert_service.py` line 29  
`pothole.get('risk_score', 0)` returns `None` (not `0`) when the key exists with a `None` value. Then `:.1f` format on `None` raises `TypeError`. Same for `age_days` on line 69.  
**Fix:** Use `pothole.get('risk_score') or 0` (which handles both missing key and `None` value).

### C6. Dockerfile and render.yaml are broken for Render deployment
**Files:** `Backend/Dockerfile`, `Backend/render.yaml`  
The Dockerfile uses `COPY Backend/cortex/requirements.txt` (repo-root context paths), but `render.yaml` sets `rootDir: Backend`, changing the build context. Result: Docker `COPY` commands fail because paths don't exist inside the `Backend/` directory.  
The `render.yaml` also uses `runtime: python` alongside a Dockerfile — Render ignores the Dockerfile when `runtime: python` is set.  
The `startCommand: uvicorn Backend.app.main:app` uses the repo-root module path, but from inside `Backend/`, it should be `app.main:app`.  
**Fix:** Either: (a) Remove `runtime: python` from render.yaml and fix Dockerfile COPY paths for `rootDir: Backend`, or (b) Remove the Dockerfile and fix the `startCommand` module path to `app.main:app` with `rootDir: Backend`.

---

## HIGH — Should Fix Before Demo

### H1. No React Error Boundary — white screen on any render error
**Files:** `Frontend/src/App.tsx`, `Frontend/src/main.tsx`  
No `ErrorBoundary` component anywhere. If `PotholeMap` (Leaflet-dependent) or any component throws, the entire React tree crashes to a white screen with no recovery.  
**Fix:** Wrap `<AppShell>` in a React error boundary that shows a fallback UI.

### H2. Latitude/longitude fallback to (0, 0) — markers in the Atlantic Ocean
**File:** `Frontend/src/api/potholes.ts` lines 44-53  
When GeoJSON features have no coordinates, `lat` and `lng` default to `0`. Markers at (0°, 0°) appear in the Gulf of Guinea and distort map viewport bounds.  
**Fix:** Skip potholes with missing coordinates (filter them out in `mapGeoJSONProperties` or in the map component).

### H3. Alert mutation state persists across pothole changes
**File:** `Frontend/src/components/PotholeDetail.tsx` lines 31-33, 157-165  
`useMutation` state (`isSuccess`, `data`) persists when switching between potholes. After sending an alert for pothole A, switching to pothole B still shows "Alert sent successfully".  
**Fix:** Reset mutation state when `pothole` changes: `useMutation({ ..., onMutate: () => { /* reset */ } })` or use `queryClient.clear()`.

### H4. `PotholeDetail` component missing keys for AnimatePresence
**File:** `Frontend/src/components/PotholeDetail.tsx` lines 38-171  
The `motion.button` and `motion.aside` inside `AnimatePresence` have no `key` prop. When switching from one pothole to another, Framer Motion can't distinguish the old from the new, so exit/enter animations don't trigger.  
**Fix:** Add `key={pothole.unique_key}` to the `motion.aside` element.

### H5. No loading/error state for pothole detail fetch
**File:** `Frontend/src/pages/MapPage.tsx` lines 78-82  
Only `data` is destructured from the detail query. No `isLoading` or `error` handling. When clicking a pothole, the detail panel shows stale GeoJSON summary data until the detail API resolves, with no spinner or error state.  
**Fix:** Destructure `isLoading` and `error` from the query and render a loading skeleton or error message.

### H6. `PotholeFilterParams.borough` regex rejects uppercase input
**File:** `Backend/app/schemas.py` line 55  
Pattern `^(Manhattan|Brooklyn|Queens|Bronx|Staten Island)$` requires title case. The database stores UPPERCASE. The frontend sends whatever the user selects. If the frontend sends "MANHATTAN", Pydantic rejects it with 422.  
**Fix:** Change regex to case-insensitive: `pattern="^(?i)(Manhattan|Brooklyn|Queens|Bronx|Staten Island)$"` or normalize to uppercase before validation.

### H7. `sent_at` column never populated in alert inserts
**File:** `Backend/app/database.py` lines 222-226  
The `INSERT INTO alerts` statement doesn't include `sent_at`. The column is `NULL` for all rows, breaking `ORDER BY sent_at DESC` in `get_alert_history`.  
**Fix:** Add `sent_at` to the INSERT statement with `datetime.now(timezone.utc).isoformat()`.

### H8. `sentence-transformers` in requirements will break Render free-tier builds
**File:** `Backend/requirements.txt`  
`sentence-transformers>=2.2.0` pulls in PyTorch (~2GB+). Render free tier has a 15-minute build timeout and 512MB RAM. The build will OOM or timeout.  
**Fix:** Move `sentence-transformers` to a separate `cortex/requirements.txt` and only install it during model training, not API deployment. The API doesn't use it — it falls back to heuristic mode.

### H9. `/alerts/report` endpoint is unauthenticated and unrate-limited
**File:** `Backend/app/alerts.py` line 160  
`POST /alerts/report` has no API key check and no rate limiter. Anyone can trigger bulk email alerts.  
**Fix:** Add `Depends(verify_admin_key)` and `@limiter.limit()` decorator.

### H10. Two conflicting ETL modules with different normalization
**Files:** `Backend/app/etl.py` line 44 vs `Backend/app/services/etl.py` line 75  
`app/etl.py` lowercases status: `str.lower().str.strip()`  
`app/services/etl.py` capitalizes status: `str.strip().str.capitalize()`  
Depending on which ETL path processes data, `status` is stored as either "open"/"closed" or "Open"/"Closed". This creates data inconsistency.  
**Fix:** Pick one normalization and apply it consistently. Delete the unused ETL module.

---

## MEDIUM — Should Fix Eventually

### M1. Heuristic probabilities don't sum to 1.0
**File:** `Backend/app/main.py` lines 265-269  
`prob_low + prob_medium + prob_high + prob_critical` can sum to >1.0 (e.g., for `prob=0.5`, sum=1.1). Labels like "probability" are misleading when they exceed 1.0.  
**Fix:** Normalize to sum to 1.0, or change labels to "score" instead of "probability".

### M2. `matchesFilters()` ignores `min_risk` and `urgency` filters
**File:** `Frontend/src/utils/map.ts` lines 136-146  
Only `borough` and `status` are checked. When the backend is unreachable and mock data is used, `min_risk` and `urgency` filters are silently ignored.  
**Fix:** Add `min_risk` and `urgency` checks to `matchesFilters()`.

### M3. `useDeferredValue` on API query key causes laggy filter UX
**File:** `Frontend/src/pages/MapPage.tsx` line 64  
`useDeferredValue(filters)` delays the API query key. UI controls update immediately but map data lags behind, creating a visible disconnect. React Query already handles caching and debouncing — `useDeferredValue` adds unnecessary delay.  
**Fix:** Remove `useDeferredValue` and use `filters` directly in the query key.

### M4. Thread-unsafe global model loading
**Files:** `Backend/app/main.py` line 126, `Backend/app/models/ml_models.py` line 13, `Backend/cortex/model.py` line 196  
`_model` global is not thread-safe. In uvicorn with multiple workers, two threads can race to load the model, resulting in double-loading or returning a partially initialized model.  
**Fix:** Use `threading.Lock` around model loading.

### M5. `admin/refresh` secret passed as URL query parameter
**File:** `Backend/app/main.py` line 364  
`secret` is a `Query(...)` parameter, appearing in server logs, browser history, and referrer headers.  
**Fix:** Change to `Header(...)` like the alert auth, or use `Depends(verify_admin_key)`.

### M6. Duplicate admin refresh buttons with desynced state
**Files:** `Frontend/src/pages/Dashboard.tsx` lines 27-35, `Frontend/src/components/AppShell.tsx` lines 10-25  
Both define independent `refreshMutation` instances. Clicking one doesn't update the other's loading/success state. Both can fire simultaneously.  
**Fix:** Lift the refresh mutation to a shared context or remove one of the buttons.

### M7. `pd.to_numeric(None)` crash when latitude column missing
**File:** `Backend/cortex/data.py` line 338  
`df.get("latitude")` returns `None` if the column doesn't exist. `pd.to_numeric(None)` raises `TypeError`.  
**Fix:** Check column existence before calling `pd.to_numeric`, or use `df.get("latitude", pd.Series(dtype=float))`.

### M8. XGBoost `use_label_encoder=False` deprecation warning
**Files:** `Backend/cortex/model.py` (training), `ml/train_accident_risk.py` line 57  
XGBoost 3.2.0 (installed) has removed `use_label_encoder` parameter. Training scripts will crash. The loaded `.joblib` models work because they were saved with an older XGBoost that supported it.  
**Fix:** Remove `use_label_encoder=False` from all XGBClassifier/XGBRegressor constructors.

### M9. Database path confusion — three different `.db` files
**Files:** `Backend/potholes.db` (126KB), `MainProject/potholes.db` (20KB), `Backend/cortex/models/potholes.db` (default)  
`.env` uses `sqlite:///./potholes.db` (relative to Backend/), but `database.py` defaults to `cortex/models/potholes.db`. Different commands may use different databases.  
**Fix:** Standardize on one path and remove the others.

### M10. Frontend `VITE_ADMIN_API_KEY` default doesn't match backend
**File:** `Frontend/.env.example` line 2  
Default is `change-me` but backend expects `potholeiq-dev`. The admin alert feature fails with 401 out of the box.  
**Fix:** Set `VITE_ADMIN_API_KEY=potholeiq-dev` in `Frontend/.env` for development.

### M11. CORS wildcard headers with credentials
**File:** `Backend/app/main.py` lines 86-92  
`allow_headers=["*"]` with `allow_credentials=True` is a broad CORS policy. While origins are restricted, wildcard headers with credentials allow any custom header.  
**Fix:** Specify explicit allowed headers instead of `["*"]`.

### M12. 18MB CSV tracked in git
**File:** `Backend/data/potholes_embeddings.csv`  
This large data file bloats the repository and slows clones.  
**Fix:** Add `*.csv` to `.gitignore` (excluding `features.csv` if needed) and use `git rm --cached` to untrack it.

---

## LOW — Nice to Have

### L1. No React linter configured
No ESLint or TypeScript linting in `package.json`. Several caught issues (unused variables, non-null assertions) would be auto-detected.

### L2. First result card auto-selected but detail panel empty
**File:** `Frontend/src/pages/MapPage.tsx` line 168  
`!selectedKey && index === 0` highlights the first card, but `selectedPothole` is null so no detail shows. Confusing UX.

### L3. `formatAgeDays(0)` returns "0 days"
Semantically should be "New" or "< 1 day". Minor UX polish.

### L4. No pagination or virtualization for results list
With 3,936 potholes, rendering all visible results without virtualization can cause jank.

### L5. Accessibility: no skip link, no focus trap in detail panel, color-only risk indicators
Screen readers and keyboard users will have difficulty.

### L6. `predictPothole()` is exported but never called — dead code
**File:** `Frontend/src/api/potholes.ts` lines 156-161

### L7. Backend `.env` uses `SMTP_PASSWORD` but code reads `SMTP_PASS`
Confirmed: `.env` has `SMTP_PASSWORD=` (empty), code reads `SMTP_PASS`. Even if the value were filled in, it wouldn't be found.

### L8. Verbose 500 error message leaks internal details
**File:** `Backend/app/main.py` line 396  
`f"Refresh failed: {str(e)}"` includes raw exception strings in API responses.

### L9. `useUserLocation` doesn't clean up geolocation callback on unmount
Minor memory leak. The `getCurrentPosition` callback can fire after component unmount.

### L10. Empty `package-lock.json` files in Backend/ and root
Non-functional npm lockfiles in a Python directory. Should be removed.

---

## Test Results

| Suite | Result |
|---|---|
| Backend API tests | 30/30 passing |
| Backend ML tests | 7/7 passing (1 XGBoost serialization warning) |
| Frontend build | Success (926KB JS bundle) |
| Frontend TypeScript | No type errors |
| Bundle size warning | 926KB JS — consider code splitting |

---

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 6 |
| HIGH | 10 |
| MEDIUM | 12 |
| LOW | 10 |

**Top priority for demo readiness:** Fix C1 (SMTP env var), C4 (duplicate routers), C5 (risk_score crash), and H1 (error boundary). These will prevent visible failures during a live demo.