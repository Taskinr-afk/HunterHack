# PotholeIQ Security Review

**Date:** 2026-04-26  
**Scope:** MainProject/ (backend + frontend)  
**Commit:** e19f743 on main

---

## Summary

30 backend tests passing. 6 functional bugs fixed in this session (NULL crash in alerts, case-sensitive status queries, inverted seed probabilities, JS falsy erasure, dead query keys, stale cache invalidation). Full codebase review completed line-by-line.

This report covers both the security review of the current diff and the comprehensive project review findings.

---

## Security Findings

### Vuln 1: Unauthenticated Alert Endpoint — `alerts.py:163`

* **Severity:** HIGH
* **Category:** `auth_bypass`
* **Confidence:** 9/10
* **Description:** `POST /alerts/report` is documented as a "Public endpoint for the frontend — no API key required." It has no `Depends(verify_admin_key)` guard. Every other write endpoint on this router (`/alerts/send`, `/alerts/scan`) requires the admin API key, but `/report` does not. An unauthenticated caller can:
  1. Trigger real SMTP emails to `ALERT_EMAIL_TO` (defaults to a NYC DOT address)
  2. Inject arbitrary text into the email body via the `message` parameter
  3. Insert unlimited rows into the `alerts` SQLite table with no rate limiting
* **Exploit Scenario:** Attacker sends `POST /alerts/report?pothole_id=DEMO-00001&message=<anything>` — no auth token needed. Each request triggers an email and creates a DB row.
* **Recommendation:** Add `Depends(verify_admin_key)` to the `/report` endpoint, or add rate limiting via `@limiter.limit("5/minute")` and make the endpoint require a captcha or frontend-only token if it must remain public.

### Vuln 2: Hardcoded Default Admin Secrets — `auth.py:11`, `main.py:365`

* **Severity:** HIGH
* **Category:** `hardcoded_secrets` / `auth_bypass`
* **Confidence:** 8/10
* **Description:** `verify_admin_key` falls back to `os.getenv("ADMIN_API_KEY", "potholeiq-dev")` and `/admin/refresh` falls back to `os.getenv("ADMIN_SECRET", "potholeiq-dev")`. If these environment variables are not explicitly set in production, any requester can access all admin-protected endpoints by supplying the well-known default. The `.env.example` file commits these defaults publicly.
* **Exploit Scenario:** On a deployment where `ADMIN_API_KEY` and `ADMIN_SECRET` are not set in the environment (common during initial deployment or misconfiguration), an attacker sends `x-api-key: potholeiq-dev` to call `/alerts/send`, `/alerts/scan`, or `POST /admin/refresh?secret=potholeiq-dev`.
* **Recommendation:** Remove the default values and fail startup if the env vars are not set in production:
  ```python
  ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
  if not ADMIN_API_KEY:
      raise RuntimeError("ADMIN_API_KEY environment variable must be set")
  ```
  Alternatively, detect `ENVIRONMENT=production` and reject defaults.

### Vuln 3: STARTTLS Conditionally Skipped — `alerts.py:51`, `alert_service.py:56`

* **Severity:** MEDIUM
* **Category:** `auth_bypass` (credential exposure)
* **Confidence:** 7/10
* **Description:** Both `_send_email()` and `send_alert_email()` were modified to skip STARTTLS when `SMTP_PORT=2525`. This is intended for Mailtrap sandbox which doesn't support STARTTLS, but it means SMTP credentials are transmitted in plaintext over the network on that port. If any non-Mailtrap SMTP server is configured on port 2525, or if Mailtrap sandbox is accessed over an untrusted network, credentials are exposed.
* **Exploit Scenario:** Attacker on the same network segment captures SMTP credentials via packet sniffing when `SMTP_PORT=2525` is configured, because STARTTLS is skipped and credentials are sent in cleartext.
* **Recommendation:** Add a dedicated `SMTP_USE_TLS` environment variable instead of inferring from the port number. Default to `True`:
  ```python
  _SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
  # ...
  if _SMTP_USE_TLS:
      server.starttls()
  ```

---

## Comprehensive Bug Review (Non-Security)

### FIXED (this session)

| # | Severity | Description | Fix |
|---|----------|-------------|-----|
| 1 | CRITICAL | NULL crash in alert builders: `pothole.get('risk_score', 0):.1f` crashes when key exists with None value | Changed to `(pothole.get('risk_score') or 0):.1f` |
| 2 | CRITICAL | `/api/stats/summary` uses case-sensitive `WHERE status = 'Open'` — returns zero for lowercase data | Changed to `LOWER(status) = 'open'` |
| 3 | HIGH | Seed data probabilities inverted: all tiers had prob_critical=0.1 regardless of risk | Tier-based probability maps |
| 4 | HIGH | JS falsy erasure: `prob_high \|\| null` converts legitimate 0 to null | Changed to `typeof` checks |
| 5 | LOW | Dead `["potholes"]` query key invalidation matched no active query | Removed |
| 6 | LOW | AppShell refresh didn't invalidate any query cache | Added invalidateQueries for all 3 active keys |

### REMAINING — HIGH SEVERITY

| # | File | Issue |
|---|------|-------|
| H1 | `main.py:204-207` | `/potholes/{unique_key}` returns raw SQLite dict — missing ML fields (accident_risk, prob_*, repair_eta) |
| H2 | `alerts.py` + `alerts_api.py` | Duplicate `/alerts/send` and `/alerts/history` routes with different auth and response shapes |
| H3 | `main.py:126-136` + `ml_models.py:12-23` | Dual global `_model` caches can desync; `/admin/refresh` only resets main.py's |
| H4 | `database.py:222-228` | `insert_alert` never sets `sent_at` — all alert timestamps are NULL |

### REMAINING — MEDIUM SEVERITY

| # | File | Issue |
|---|------|-------|
| M1 | `app/etl.py:43` | Status normalized to lowercase but other ETL paths use capitalized |
| M2 | `api/stats.py:70-82` | Hard-coded `WHERE created_date > '2024-01-01'` filter |
| M3 | `services/geospatial.py:14`, `services/impact.py:7` | Absolute imports (`from app.database`) may break outside module context |
| M4 | `main.py:364` | Admin secret passed as query parameter (visible in logs) |
| M5 | `database.py:24` | `ALERT_COLS` doesn't include `status` column; computed from `delivered` instead |
| M6 | Frontend `api/potholes.ts:140-150` | Client re-computes `repair_eta` instead of using backend value |
| M7 | Frontend `mockData.ts:38-69` | Mock data omits `accident_probability`, `prob_*`, `aadt` fields |
| M8 | Frontend `types/index.ts` | `BoroughStats` name collides with backend `BoroughStats` (different shape) |

### REMAINING — LOW SEVERITY

| # | File | Issue |
|---|------|-------|
| L1 | Frontend `App.tsx`/`main.tsx` | No React error boundary — render crash = white screen |
| L2 | Frontend `PotholeDetail.tsx:32` | `pothole!` non-null assertion can crash if triggered programmatically |
| L3 | Frontend `potholes.ts:44-53` | Fallback coordinates (0, 0) render markers in Gulf of Guinea |
| L4 | Frontend `PotholeDetail.tsx:41-168` | `AnimatePresence` children lack `key` props — exit animations may not fire |
| L5 | Frontend `hooks/useViewportPotholes.ts:20-33` | `useViewportPotholes` hook is dead code (never called) |
| L6 | Frontend `api/client.ts:5` | `VITE_API_BASE_URL || "http://localhost:8000"` prevents proxy activation (use `??`) |

---

## What's Working Well

- 30/30 backend tests passing with comprehensive schema and security checks
- Canonical schema enforcement: `unique_key`, `age_days`, `risk_score`, `nearby_crashes` — no alias leaks
- Security headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
- CORS configuration with configurable origins
- Rate limiting on all public endpoints (60/min GeoJSON, 120/min detail, 30/min predict)
- Heuristic fallback for `/predict` when ML models aren't loaded
- React Query caching with 5-min staleTime, proper refetch on admin refresh
- Frontend gracefully falls back to mock data when backend is unreachable
- Parameterized SQL queries throughout — no injection risk
- Pydantic input validation on all endpoints