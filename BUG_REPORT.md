# PotholeIQ — Full Project Bug Report

> Generated 2026-04-26. Covers backend, frontend, ML pipeline, config, and cross-cutting concerns.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 5 |
| HIGH | 13 |
| MEDIUM | 20 |
| LOW | 15 |

---

## CRITICAL BUGS

### B-01. Hardcoded default secrets in production paths
**Files:** `Backend/app/auth.py:11`, `Backend/app/main.py:369`

Two different hardcoded defaults — `"potholeiq-dev"` — protect admin endpoints:
- `ADMIN_API_KEY` (alerts, via `x-api-key` header)
- `ADMIN_SECRET` (data refresh, via query param)

If neither env var is set, anyone can authenticate with the known default. Different var names mean they can drift apart.

**Impact:** Full admin access to any deployment that doesn't explicitly set both env vars.

---

### B-02. Unauthenticated `/alerts/report` endpoint
**File:** `Backend/app/alerts.py:163`

`POST /alerts/report` has no auth, no API key requirement, and no rate limiting. It accepts arbitrary `pothole_id` values and triggers alert emails.

**Impact:** Unauthenticated users can flood the DOT alert system with spam.

---

### B-03. `Content-Type` header silently dropped when custom headers are passed
**File:** `Frontend/src/api/client.ts:7-14`

```ts
const opts: RequestInit = {
  headers: { "Content-Type": "application/json", ...options.headers },
  ...options,
};
```

The spread `...options` comes _last_, which means `options.headers` overwrites the merged `headers` object. When `sendAlert` passes `{ "x-api-key": ADMIN_API_KEY }`, the `Content-Type: application/json` header is lost. The server then fails to parse the JSON body.

**Impact:** The "Send DOT alert" button silently fails with a 422 error.

---

### B-04. `render.yaml` startCommand has wrong module path
**File:** `Backend/render.yaml:7`

```
startCommand: uvicorn Backend.app.main:app --host 0.0.0.0 --port $PORT
```

`render.yaml` sets `rootDir: Backend`, so the working directory is already inside `Backend/`. The start command should be `uvicorn app.main:app`, not `uvicorn Backend.app.main:app`.

**Impact:** Render deployment crashes with `ModuleNotFoundError: No module named 'Backend'`.

---

### B-05. 18MB+ data/model files tracked in git
**Files:** `kevin/cortex/models/potholes.db` (1.3MB), `MainProject/Backend/data/potholes_embeddings.csv` (18MB), etc.

The `.gitignore` patterns don't cover the `kevin/` directory or `MainProject/Backend/data/` (only `data/raw/`). Model artifacts, CSVs, and SQLite databases are committed.

**Impact:** Bloated repository; regenerated artifacts should not be version-controlled.

---

## HIGH BUGS

### B-06. Duplicate alert routes with different implementations
**Files:** `Backend/app/alerts.py:90`, `Backend/app/api/alerts_api.py:17`

Two `POST .../send` endpoints exist:
- `/alerts/send` — query params, custom SMTP, returns `{sent_at, ...}`
- `/api/alerts/send` — JSON body with `AlertRequest` schema, uses `alert_service.py`, returns `AlertResponse` with `sent_date`

Similarly two `/history` routes with different response shapes. The frontend only calls `/api/alerts/send`, but the old route is still active.

**Impact:** API consumers hitting the wrong route get different behavior. Maintenance confusion.

---

### B-07. `POTHOLE_COLS` missing `location_type` — breaks ML `is_highway` feature
**File:** `Backend/app/database.py:16-20`

`POTHOLE_COLS` does not include `location_type`. When `predict_for_pothole()` in `ml_models.py` creates a DataFrame from the queried row, `location_type` is absent. `build_features()` then fails to compute `is_highway` correctly (always gets NaN → 0).

The `/predict` endpoint in `main.py` adds default empty columns (`for col in ("location_type", ...): df[col] = ""`), but `ml_models.py`'s `predict_for_pothole()` does **not** add these defaults.

**Impact:** Single-pothole prediction via `/api/predictions/{id}` crashes or produces wrong results for highway potholes.

---

### B-08. Two conflicting risk-scoring formulas
**Files:** `Backend/cortex/features.py:126-158`, `Backend/app/services/impact.py:25-110`

`cortex/features.py` risk formula (6 weighted features totaling 100pts):
```
age(40) + traffic_ATR(15) + AADT(10) + severity(15) + highway(8) + crashes(12)
```

`impact.py` risk formula (3 features):
```
0.40 * crash_factor + 0.30 * age_factor + 0.30 * traffic_factor
```

These produce fundamentally different scores for the same pothole. `impact.py` writes directly to the DB, overwriting any ML model scores.

**Impact:** Inconsistent risk scores depending on which scoring path ran last.

---

### B-09. Missing database indexes
**File:** `Backend/app/database.py:47-88`

`init_db()` creates no indexes beyond the primary key. Queries filtering on `status`, `borough`, `risk_score`, `urgency_label`, and `unique_key` (lookup) all do full table scans. The `get_high_risk_unalerted()` function runs a correlated subquery with no index on `alerts.pothole_id` or `alerts.delivered`.

**Impact:** Significant performance degradation as dataset grows (50K+ rows).

---

### B-10. Race condition in `scan_and_alert`
**Files:** `Backend/app/database.py:241-256`, `Backend/app/alerts.py:127-154`

`/alerts/scan` reads high-risk unalerted potholes, then iterates and inserts alerts. Two concurrent requests can both read the same "unalerted" potholes before either writes, sending duplicate alerts.

**Impact:** Duplicate DOT alert emails during concurrent scan requests.

---

### B-11. `POTHOLE_COLS` also missing `zip_code` and `pavement_crash_nearby` from API responses
**File:** `Backend/app/database.py:16-20`

`POTHOLE_COLS` excludes `zip_code`, `location_type`, and `pavement_crash_nearby`. Tests assert this is intentional for security (`zip_code`) and design reasons. However, `pavement_crash_nearby` is computed by the ML pipeline and stored in the DB but never returned to the frontend.

**Impact:** `pavement_crash_nearby` data is lost on the frontend. The GeoJSON endpoint adds it to `PotholeProperties`, but the frontend's `mapGeoJSONProperties` doesn't map it.

---

### B-12. Frontend `PotholeDetail` latitude type mismatch
**File:** `Frontend/src/types/index.ts:34-35`

`PotholeDetail` has `latitude?: number | null` and `longitude?: number | null`, but `Pothole` (which the detail panel component receives) requires `latitude: number` and `longitude: number`. The merge in `MapPage.tsx` falls back to `DEFAULT_CENTER` coordinates when the detail response has null lat/lng.

**Impact:** Pothole detail panel could show a pin at NYC center coordinates instead of actual location with no visual indication the coordinates are synthetic.

---

### B-13. Confusing dual `accident_risk_probability` / `accident_probability` fields
**Files:** `Backend/app/schemas.py:34-35`, `Backend/app/main.py:191-195`

The schema defines both `accident_risk_probability` and `accident_probability`. In the GeoJSON endpoint, `accident_risk_probability = prob_high + prob_critical`. In the heuristic fallback, `accident_probability` is computed from a different formula. The frontend `PotholeFeature` type includes both fields.

**Impact:** Consumers don't know which field to display. Different endpoints return different values for semantically similar fields.

---

### B-14. Frontend `StatsResponse` type does not match backend `StatsResponse` schema
**Files:** `Frontend/src/types/index.ts:88-91`, `Backend/app/schemas.py:143-151`

Frontend type: `{ summary: StatsSummary, timeline: TimelinePoint[] }`
Backend schema: `{ total_potholes, open_potholes, critical, high, medium, low, avg_risk_score, by_borough }`

These are completely unrelated shapes sharing the same type name. The frontend constructs its `StatsResponse` by composing two separate API calls (`/api/stats/summary` + `/api/stats/timeline`), while the backend's `/stats` endpoint returns a monolithic response the frontend never calls.

**Impact:** If anyone calls the monolithic `/stats` endpoint expecting the frontend type, runtime crash.

---

### B-15. Dockerfile missing `sentence-transformers` from split requirements
**File:** `Backend/Dockerfile:9-11`

The Dockerfile copies `Backend/cortex/requirements.txt` and `Backend/app/requirements.txt` separately, but `sentence-transformers` (which requires PyTorch, ~2GB) only exists in the consolidated `Backend/requirements.txt`.

**Impact:** Docker container missing `sentence-transformers`; `cortex/embed.py` import fails at runtime.

---

### B-16. `admin/refresh` endpoint uses query param for secret
**File:** `Backend/app/main.py:368`

```python
def admin_refresh(secret: str = Query(...)):
```

The admin secret is passed as a URL query parameter, exposing it in browser history, server logs, and proxy logs.

**Impact:** Secret exposed in logs and URLs; inconsistent with alert endpoints which use `x-api-key` header.

---

### B-17. Tooltip always shows "open" regardless of pothole status
**File:** `Frontend/src/components/PotholeMap.tsx:119`

```tsx
{pothole.borough} | {formatAgeDays(pothole.age_days)} open
```

The word "open" is hardcoded. A closed pothole displays "5 days open" when it's actually been closed for 5 days.

**Impact:** Misleading tooltip on every closed pothole marker.

---

### B-18. Heuristic probability values do not sum to 1.0
**Files:** `Backend/app/main.py:269-275`, `Backend/app/models/ml_models.py:94-99`

```python
prob_low = round(max(1 - prob, 0), 3)      # e.g. 0.2
prob_medium = round(min(prob * 0.5, 0.5), 3) # e.g. 0.4
prob_high = round(min(prob * 0.4, 0.4), 3)   # e.g. 0.32
prob_critical = round(min(prob * 0.3, 0.3), 3) # e.g. 0.24
# Total = 1.16 for prob=0.8
```

The four probabilities can sum to more than 1.0.

**Impact:** Frontend displaying probability distributions shows >100% total.

---

## MEDIUM BUGS

### B-19. Status case mismatch between ETL pipelines
**Files:** `Backend/app/etl.py:75` (capitalizes: "Open"/"Closed"), `Backend/app/services/etl.py:44` (lowercases: "open"/"closed"), `Backend/cortex/data.py:351` (uppercases borough, no status normalization)

Three different normalization strategies. `impact.py` filters `WHERE status = 'Open'` (capitalized), which breaks if data was loaded via the lowercase pipeline.

**Impact:** Impact scoring returns zero results when data uses lowercase status values.

---

### B-20. Duplicate ETL pipelines that can conflict
**Files:** `Backend/app/etl.py`, `Backend/app/services/etl.py`, `Backend/cortex/data.py`

Three overlapping data-fetching modules with different column naming, status normalization, and join logic. The `/admin/refresh` endpoint mixes `cortex.data.fetch_all()` with `validate_pothole_data()` from `app/services/etl.py`.

**Impact:** Data conflicts if more than one pipeline is used.

---

### B-21. `insert_alert` does not set `sent_at`
**File:** `Backend/app/database.py:220-228`

The INSERT statement omits `sent_at`, leaving it NULL. Alert history ordered by `sent_at DESC` sorts NULLs first, and the API maps `sent_at → sent_date` which becomes empty string.

**Impact:** Alert history always shows empty/missing dates for newly created alerts.

---

### B-22. N+1 query problem in `get_stats()`
**File:** `Backend/app/database.py:167-205`

`get_stats()` executes 31 separate SQL queries (6 for overall stats + 5 per borough × 5 boroughs). This could be replaced with a single `GROUP BY` query.

**Impact:** Slow stats endpoint under load.

---

### B-23. Row-by-row `upsert_potholes` is extremely slow
**File:** `Backend/app/database.py:151-162`

Uses `iterrows()` to insert one row at a time. For 50K potholes, this means 50K individual SQL executions.

**Impact:** `/admin/refresh` could take minutes to complete.

---

### B-24. `_cached_model` not reset on admin refresh
**File:** `Backend/app/main.py:384-385` resets `_model = None` but not `cortex/model.py::_cached_model`

After `/admin/refresh`, the model file may be retrained, but `score_potholes()` still uses the stale cached model.

**Impact:** Stale ML predictions after admin refresh until server restart.

---

### B-25. Frontend `matchesFilters` ignores `min_risk`, `urgency`, `limit`
**File:** `Frontend/src/utils/map.ts:136-146`

Only checks `borough` and `status`. The `PotholeFilters` type defines `min_risk`, `urgency`, and `limit` fields, but they are never enforced client-side.

**Impact:** Any UI filters for risk level, urgency, or result limit would have no effect.

---

### B-26. Frontend `buildMockSummary` divides by zero when potholes array is empty
**File:** `Frontend/src/utils/mockData.ts:114`

`potholes.reduce(...) / potholes.length` produces `NaN` when `potholes.length === 0`.

**Impact:** Dashboard shows "NaN" if mock data is somehow empty.

---

### B-27. Frontend `useUserLocation` has no cleanup for geolocation callback
**File:** `Frontend/src/hooks/useUserLocation.ts:22-50`

`navigator.geolocation.getCurrentPosition` callbacks can fire after component unmount, causing state updates on unmounted component.

**Impact:** React warnings; potential memory leak.

---

### B-28. AppShell toast timeouts never cleaned up on unmount
**File:** `Frontend/src/components/AppShell.tsx:18,23`

`setTimeout(() => setToast(null), 5000)` and `setTimeout(() => setToast(null), 8000)` are never cleared on unmount.

**Impact:** React warnings; potential memory leak.

---

### B-29. Frontend auto-selects first pothole on page load
**File:** `Frontend/src/pages/MapPage.tsx:168`

```tsx
selected={... || (!selectedKey && index === 0)}
```

When no pothole is selected, the first result is auto-highlighted. The detail panel opens on page load without user action.

**Impact:** Unexpected auto-selection; detail panel opens on page load.

---

### B-30. `DATABASE_URL` default mismatch between `.env.example` and code
**Files:** `Backend/.env.example` (`sqlite:///./potholes.db`), `Backend/app/database.py:12-13` (defaults to `cortex/models/potholes.db`)

If someone copies `.env.example` without modification, the app creates an empty `potholes.db` in CWD instead of using the seeded database.

**Impact:** Demo runs with empty DB instead of 3,936 potholes.

---

### B-31. Frontend `adminRefresh` exposes secret in URL
**File:** `Frontend/src/api/alerts.ts:20`

```ts
return fetchAPI(`/admin/refresh?secret=${secret}`, { method: "POST" });
```

The default secret `"potholeiq-dev"` is embedded in the frontend bundle and visible in browser devtools. The URL also appears in server logs and browser history.

**Impact:** Anyone can trigger admin data refresh by reading the frontend source.

---

### B-32. Frontend `Dashboard` doesn't guard `avg_age_days` against NaN
**File:** `Frontend/src/pages/Dashboard.tsx:78`

```tsx
<strong>{Math.round(summary.avg_age_days)}</strong>
```

If the API returns null/undefined, `Math.round(NaN)` renders as "NaN".

**Impact:** "NaN" displayed in dashboard if API returns unexpected data.

---

### B-33. `predictions.py` endpoint returns raw dict, not typed schema
**File:** `Backend/app/api/predictions.py:12-22`

No Pydantic response model is defined for `/api/predictions/{id}`. Extra keys could leak; field names are undocumented.

**Impact:** No API contract enforcement; inconsistent response shapes.

---

### B-34. Timeline query uses `strftime('%Y-%W')` which is not ISO week numbering
**File:** `Backend/app/api/stats.py:70-82`

SQLite `%W` counts weeks from the first Monday, producing `"2024-00"` for early January dates. Not the same as ISO 8601 weeks.

**Impact:** Timeline data has confusing week labels like "2024-00".

---

### B-35. `accident_risk_probability` computed differently across endpoints
**Files:** `Backend/app/main.py:191-194` (`prob_high + prob_critical`), `Backend/app/models/ml_models.py:71` (heuristic: `risk_score / 100`)

Three different computation paths return different values for the same field name.

**Impact:** Inconsistent probability values across API endpoints.

---

### B-36. `leaflet.markercluster` CSS imports depend on transitive dependency hoisting
**File:** `Frontend/src/components/PotholeMap.tsx:15-16`

```ts
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
```

`leaflet.markercluster` is not a direct dependency — it's a transitive dep of `react-leaflet-cluster`. If npm doesn't hoist it, these imports fail at build time.

**Impact:** Build failure or broken cluster marker styles depending on npm hoisting.

---

### B-38. `upsert_potholes` does not write `scored_at` column
**File:** `Backend/app/database.py:139-145`

The column list omits `scored_at`, so it's always NULL despite the column existing in the table schema.

**Impact:** ML scoring timestamp is lost; `scored_at` is always NULL.

---

## LOW BUGS

### B-39. `impact.py` uses absolute import `from app.database`
**File:** `Backend/app/services/impact.py:12`

Uses `from app.database import get_conn` instead of relative import. Fails if `app` is not on `sys.path`.

**Impact:** `ModuleNotFoundError` depending on how the server is started.

---

### B-40. `geospatial.py` uses absolute import
**File:** `Backend/app/services/geospatial.py:14`

Same issue as B-39.

---

### B-41. `traffic_volume` zero values converted to `None`
**File:** `Backend/app/models/ml_models.py:58`

```python
"traffic_volume": int(pothole.get("traffic_volume") or 0) or None,
```

`int(0 or 0) or None` → `0 or None` → `None`. Legitimate zero traffic volumes become null.

**Impact:** Data loss; zero traffic reported as unknown.

---

### B-42. `formatAgeDays` uses imprecise month calculation
**File:** `Frontend/src/utils/map.ts:67`

`days / 30` is an approximation. 90 days = "3 months" but is actually ~3.0 months.

**Impact:** Slightly inaccurate age display for long-open potholes.

---

### B-43. `normalizeStatus` defaults null/undefined to "open"
**File:** `Frontend/src/api/potholes.ts:29`

When backend sends `status: null`, it becomes "open". Potholes with missing status are incorrectly shown as active.

**Impact:** Inflated open counts for potholes with missing status data.

---

### B-44. Type assertion bypasses type safety in `mapGeoJSONProperties`
**File:** `Frontend/src/api/potholes.ts:100-101`

Casts `f.properties` through `unknown` to `Record<string, unknown>`, hiding backend schema changes.

**Impact:** API contract violations invisible at compile time.

---

### B-45. `buildMockSummary` `avg_age_days` averages across open+closed
**File:** `Frontend/src/utils/mockData.ts:100,108`

The "Avg days open" label implies only open potholes, but the calculation includes closed ones too.

**Impact:** Misleading average that understates open-pothole age.

---

### B-46. `MapContainer` center prop only used for initial render
**File:** `Frontend/src/components/PotholeMap.tsx:84`

After mount, `center` prop changes have no effect. `MapFocusController` handles subsequent updates, but there's a brief flash of the default position.

**Impact:** Brief flash of default map position before flying to user location.

---

### B-47. No focus trap in PotholeDetail panel
**File:** `Frontend/src/components/PotholeDetail.tsx:41-168`

Tab key can move focus to elements behind the backdrop.

**Impact:** Keyboard-only users can tab to background content while panel is open.

---

### B-48. No loading/error state for pothole detail query
**File:** `Frontend/src/pages/MapPage.tsx:78-82`

`isLoading` and `error` from the detail query are destructured but never used.

**Impact:** No visual feedback when detail fetch is in progress or fails.

---

### B-49. `SMTP_PORT` type mismatch between `.env.example` and code fallback
**File:** `Backend/.env.example` sets `SMTP_PORT=2525`, but code default is `587`

**Impact:** Confusing defaults; `.env.example` uses Mailtrap port, code uses Gmail port.

---

### B-50. Loose dependency version ranges with no upper bounds
**File:** `Backend/requirements.txt`

All deps use `>=` with no upper bounds. A future major version could break the app.

**Impact:** Works today but could break on fresh installs in the future.

---

### B-51. README missing all setup/run instructions
**File:** `README.md`

Says "Setup instructions per module will be added as the project is built out" but never provides actual commands.

**Impact:** New developers cannot figure out how to run the project from the README.

---

### B-52. README mentions "Mapbox GL JS" but project uses Leaflet
**File:** `README.md:61`

Tech stack says "Mapbox GL JS / Leaflet" but only Leaflet is used.

**Impact:** Misleading documentation.

---

### B-53. `.gitignore` pattern `Front-end` typo
**File:** `.gitignore:8-9`

Uses `**/Front-end/.env` but the actual directory is `Frontend` (no hyphen). The pattern never matches.

**Impact:** Frontend `.env` files could accidentally be committed (though other `.env` patterns catch this).

---

### B-54. `PotholeFilters.min_risk` typed as `string` but backend expects `float`
**File:** `Frontend/src/types/index.ts:62`

Works at runtime due to string-to-float coercion, but the TypeScript type is misleading.

**Impact:** Developer confusion; incorrect type documentation.

---

### B-55. `fix_days_estimate` type mismatch between DB (INTEGER) and heuristic (float)
**File:** `Backend/app/models/ml_models.py:82`

Heuristic fallback computes `fix_days = max(1, base_days + int(days_open // 10))`, but the DB column is `INTEGER` and the schema declares it as `int`. Pandas may store it as float.

**Impact:** Potential Pydantic validation error if value is a float from pandas.

---

## Appendix: Issue Cross-Reference

| Area | Critical | High | Medium | Low |
|------|----------|------|--------|-----|
| Backend — Auth/Security | 2 | 2 | 1 | 0 |
| Backend — Data/API | 0 | 3 | 6 | 2 |
| Backend — ML/Scoring | 0 | 2 | 2 | 1 |
| Backend — Deployment | 1 | 1 | 1 | 0 |
| Frontend — API Integration | 1 | 2 | 3 | 2 |
| Frontend — UI/UX | 0 | 1 | 2 | 4 |
| Frontend — Types/State | 0 | 1 | 2 | 2 |
| Cross-Cutting — Contract | 0 | 1 | 2 | 1 |
| Config/Infra | 1 | 0 | 1 | 4 |