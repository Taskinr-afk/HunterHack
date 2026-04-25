# Security Plan — PotholeTracker NYC

> **Audience:** Beginners who just started coding. Every step is explicit — no assumed knowledge.

---

## 0. Why Security Matters for This Project

We are building an app that:
- Fetches data from public NYC Open Data APIs
- Serves data through our own backend API
- Sends automated alerts to government systems
- Displays user-facing maps with real-time data

Even for a hackathon, security basics prevent demo-day embarrassment and show judges you think professionally.

---

## Phase 0: Pre-Work — Set Up Secrets Management

### Step 0.1: Create a `.gitignore` file
**What:** Prevent sensitive files from being committed to GitHub.

**Why:** If API keys or database files get pushed, anyone can abuse them. This is the #1 security mistake in hackathons.

**How:**
```bash
cd ~/HunterHack
cat > .gitignore << 'EOF'
# Environment variables
.env
.env.local
.env.production

# API keys
*api_key*
*secret*

# Database
*.db
*.sqlite3
potholes.db

# Python
__pycache__/
*.pyc
*.pyo
venv/
.venv/
env/
*.egg-info/

# Node
node_modules/
dist/
build/

# ML model files (large)
*.pkl
*.joblib
*.h5

# Data caches (large CSV files)
data/raw/
*.csv.gz

# IDE
.vscode/
.idea/
*.swp
.DS_Store

# OS
Thumbs.db
EOF
git add .gitignore
git commit -m "Add .gitignore to prevent secrets and large files from being committed"
```

**Verify:** `git status` should NOT show `.env` or `.db` files when you create them.

---

### Step 0.2: Create a `.env` file for secrets
**What:** Store all API keys and secrets in one file that is never committed.

**How:**
```bash
cat > .env << 'EOF'
# Mapbox (for map tiles)
MAPBOX_ACCESS_TOKEN=pk.your_mapbox_token_here

# NYC Open Data (SODA API — public, no key needed for basic access)
# If you get an app token for higher rate limits, put it here:
NYC_OPENDATA_APP_TOKEN=your_app_token_here

# Email alerts (SMTP — for alert system)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password_here
ALERT_RECIPIENT_EMAIL=nyc_dot_borough@example.com

# Database
DATABASE_URL=sqlite:///./potholes.db

# Flask/FastAPI
SECRET_KEY=change-this-to-a-random-string-at-least-32-chars
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
EOF
```

**Critical:** NEVER run `git add .env`. The `.gitignore` protects it, but double-check:
```bash
git status  # .env should NOT appear in the list
```

---

### Step 0.3: Create `.env.example` (safe template to commit)
**What:** A version of `.env` with fake values that teammates can copy.

**How:**
```bash
cat > .env.example << 'EOF'
# Copy this file to .env and fill in your real values
# NEVER commit your real .env file!

MAPBOX_ACCESS_TOKEN=pk.your_mapbox_token_here
NYC_OPENDATA_APP_TOKEN=your_app_token_here
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password_here
ALERT_RECIPIENT_EMAIL=example@example.com
DATABASE_URL=sqlite:///./potholes.db
SECRET_KEY=change-this-to-a-random-string
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
EOF
git add .env.example
git commit -m "Add .env.example template (safe to commit, no real secrets)"
```

---

## Phase 1: Backend API Security

### Step 1.1: Install and configure CORS
**What:** Cross-Origin Resource Sharing (CORS) controls which websites can call your API.

**Why:** Without CORS configuration, any website can call your API. With it configured, only your frontend can.

**How (FastAPI):**
```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="PotholeTracker NYC", version="1.0.0")

# Read allowed origins from .env
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Only allow YOUR frontend
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Only methods you actually use
    allow_headers=["*"],
)
```

**Anti-pattern to avoid:**
```python
# NEVER DO THIS — allows ALL websites to call your API
allow_origins=["*"]
```

**Verify:** Start the backend, open a browser console on a different domain, and confirm the request is blocked.

---

### Step 1.2: Add rate limiting
**What:** Limit how many requests a single IP can make per minute.

**Why:** Prevents abuse and accidental DoS from runaway frontend loops.

**How:**
```bash
pip install slowapi
```

```python
# backend/app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to endpoints
@app.get("/api/potholes")
@limiter.limit("100/minute")  # 100 requests per minute per IP
async def get_potholes(request: Request):
    ...
```

---

### Step 1.3: Input validation on all API endpoints
**What:** Never trust user input. Validate and sanitize everything.

**Why:** Prevents SQL injection, path traversal, and unexpected crashes.

**How (FastAPI with Pydantic):**
```python
# backend/app/schemas.py
from pydantic import BaseModel, Field, validator
from typing import Optional
import re

class PotholeFilterParams(BaseModel):
    borough: Optional[str] = Field(None, pattern="^(Manhattan|Brooklyn|Queens|Bronx|Staten Island)$")
    status: Optional[str] = Field(None, pattern="^(open|closed)$")
    limit: int = Field(100, ge=1, le=1000)  # Between 1 and 1000
    offset: int = Field(0, ge=0)

class AlertRequest(BaseModel):
    pothole_id: str = Field(..., min_length=1, max_length=50)
    message: Optional[str] = Field(None, max_length=2000)

    @validator("pothole_id")
    def validate_pothole_id(cls, v):
        # Only allow alphanumeric + hyphens — no SQL injection possible
        if not re.match(r"^[a-zA-Z0-9\-]+$", v):
            raise ValueError("Invalid pothole ID format")
        return v
```

**Verify:** Send a request with `borough="<script>alert(1)</script>"` and confirm it's rejected.

---

### Step 1.4: Use parameterized database queries
**What:** Never build SQL queries by concatenating strings.

**Why:** String concatenation allows SQL injection attacks.

**How (SQLite with Python):**
```python
# backend/app/database.py
import sqlite3
from contextlib import contextmanager

DB_PATH = "potholes.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return dict-like rows
    try:
        yield conn
    finally:
        conn.close()

# GOOD — parameterized query (safe from SQL injection)
def get_potholes(borough: str = None, status: str = None, limit: int = 100, offset: int = 0):
    with get_db() as conn:
        query = "SELECT * FROM potholes WHERE 1=1"
        params = []
        if borough:
            query += " AND borough = ?"  # ? placeholder — SAFE
            params.append(borough)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_date DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return conn.execute(query, params).fetchall()

# BAD — NEVER DO THIS:
# query = f"SELECT * FROM potholes WHERE borough = '{borough}'"  # SQL INJECTION RISK
```

**Verify:** Test with `borough="'; DROP TABLE potholes;--"` and confirm it's safely handled (not executed).

---

### Step 1.5: Secure the alert endpoint
**What:** The alert-sending endpoint is powerful — only authorized requests should trigger it.

**Why:** Without protection, anyone can spam the DOT with fake alerts.

**How (simple API key auth for hackathon):**
```python
# backend/app/auth.py
from fastapi import Header, HTTPException
import os

API_KEY = os.getenv("ADMIN_API_KEY", "change-me-in-production")

async def verify_admin_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

# Usage in main.py:
from backend.app.auth import verify_admin_key
from fastapi import Depends

@app.post("/api/alerts/send")
async def send_alert(alert: AlertRequest, authorized=Depends(verify_admin_key)):
    ...
```

Add to `.env`:
```
ADMIN_API_KEY=your-random-secret-key-here
```

**For production** (not hackathon), upgrade to proper OAuth2/JWT.

---

## Phase 2: Data Security

### Step 2.1: Sanitize data before serving to frontend
**What:** Remove or redact sensitive fields from API responses.

**Why:** NYC 311 data may contain complainant names, phone numbers, or addresses you don't need to expose.

**How:**
```python
# backend/app/schemas.py (response models)
class PotholeResponse(BaseModel):
    id: str
    latitude: float
    longitude: float
    borough: str
    status: str
    created_date: str
    closed_date: Optional[str]
    days_open: int
    descriptor: str
    # Notice: NO personal info fields like complainant_name, phone, etc.

class PotholeDetailResponse(PotholeResponse):
    impact_score: Optional[float]
    accident_risk: Optional[str]       # LOW / MEDIUM / HIGH
    predicted_repair_days: Optional[int]
    nearby_collision_count: int
    traffic_volume: Optional[int]
```

When querying the database, only SELECT the fields you need:
```python
# Explicitly list columns — never use SELECT *
query = """
    SELECT id, latitude, longitude, borough, status,
           created_date, closed_date, days_open, descriptor,
           impact_score
    FROM potholes
    WHERE status = 'open'
"""
```

---

### Step 2.2: Validate external data before storing
**What:** NYC Open Data is generally clean, but never assume.

**How:**
```python
# backend/app/etl.py
import pandas as pd

def validate_pothole_data(df: pd.DataFrame) -> pd.DataFrame:
    # Remove rows without coordinates
    df = df.dropna(subset=["latitude", "longitude"])

    # Validate coordinate ranges (NYC bounds)
    df = df[
        (df["latitude"].between(40.4, 41.0)) &
        (df["longitude"].between(-74.3, -73.7))
    ]

    # Strip whitespace from text fields
    df["borough"] = df["borough"].str.strip()
    df["status"] = df["status"].str.strip().str.lower()

    # Validate status values
    df = df[df["status"].isin(["open", "closed"])]

    return df
```

---

## Phase 3: Frontend Security

### Step 3.1: Never store secrets in frontend code
**What:** API keys in React code are visible to anyone who opens DevTools.

**How:**
```javascript
// frontend/src/config.js

// GOOD — use backend proxy for any API that needs a key
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// BAD — NEVER put real API keys in frontend code:
// const MAPBOX_KEY = "pk.eyJ1..."  // Anyone can steal this from your bundle

// If you MUST use Mapbox in the frontend, use the public token
// (Mapbox tokens are designed to be public, but scope them to your domain)
export const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || "";
```

Create `frontend/.env`:
```
VITE_API_BASE_URL=http://localhost:8000
VITE_MAPBOX_TOKEN=pk.your_public_token_here
```

Create `frontend/.env.example`:
```
VITE_API_BASE_URL=http://localhost:8000
VITE_MAPBOX_TOKEN=pk.your_mapbox_public_token_here
```

Add to `.gitignore` (already covered by the `.env` pattern, but be explicit):
```
frontend/.env
```

---

### Step 3.2: Sanitize rendered data
**What:** Prevent XSS (Cross-Site Scripting) — don't render raw HTML from external data.

**Why:** NYC 311 data is user-submitted. Someone could put `<script>alert('xss')</script>` in a complaint.

**How:**
```jsx
// BAD — dangerously rendering raw HTML
<div dangerouslySetInnerHTML={{ __html: pothole.descriptor }} />

// GOOD — React escapes strings by default
<div>{pothole.descriptor}</div>

// If you NEED formatted text, use a sanitizer:
// npm install dompurify
import DOMPurify from "dompurify";
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(pothole.descriptor) }} />
```

---

### Step 3.3: Set security headers
**What:** HTTP headers that tell browsers to enforce security rules.

**How (FastAPI middleware):**
```python
# backend/app/main.py
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://api.mapbox.com; "
            "img-src 'self' data: https://*.tile.openstreetmap.org https://api.mapbox.com; "
            "connect-src 'self' https://api.mapbox.com https://data.cityofnewyork.us"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

---

## Phase 4: Deployment Security

### Step 4.1: Set environment variables on hosting platform
**What:** Never hardcode production secrets. Use the hosting platform's secret management.

**For Vercel (frontend):**
```bash
# In Vercel dashboard → Settings → Environment Variables
VITE_API_BASE_URL=https://your-backend.onrender.com
VITE_MAPBOX_TOKEN=pk.your_production_token
```

**For Render/Railway (backend):**
```bash
# In Render dashboard → Environment
DATABASE_URL=postgresql://user:pass@host/db
SECRET_KEY=a-real-random-32-char-string
ALLOWED_ORIGINS=https://your-frontend.vercel.app
SMTP_PASSWORD=your-real-smtp-password
```

---

### Step 4.2: Enable HTTPS only
**What:** Force all traffic to use HTTPS.

**Why:** HTTP sends everything in plain text — including API keys and user data.

**How:** Most hosting platforms (Vercel, Render, Railway) enforce HTTPS by default. If not:

```python
# backend/app/main.py
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

# In production only:
if os.getenv("ENVIRONMENT") == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
```

---

### Step 4.3: Pre-deployment security checklist
Run through this before going live:

```markdown
## Pre-Deploy Security Checklist

- [ ] .gitignore includes .env, *.db, *.pkl
- [ ] No real API keys committed to git (run: `git log --all -p | grep -i "api_key\|secret\|token"`)
- [ ] .env.example exists with fake values for teammates
- [ ] CORS configured to only allow your frontend origin
- [ ] All user inputs validated with Pydantic models
- [ ] All database queries use parameterized statements (?)
- [ ] Alert endpoint protected with API key
- [ ] Security headers set (CSP, X-Frame-Options, etc.)
- [ ] No dangerouslySetInnerHTML without DOMPurify
- [ ] HTTPS enforced in production
- [ ] Rate limiting configured
- [ ] Production secrets set on hosting platform (not in code)
```

---

## Quick Reference: Security Don'ts

| Don't | Why | Do Instead |
|-------|-----|-----------|
| `allow_origins=["*"]` | Any site can call your API | List your specific frontend URL |
| `SELECT *` | May leak sensitive columns | List only needed columns |
| `f"WHERE borough = '{borough}'"` | SQL injection | Use `?` parameterized queries |
| API keys in React code | Visible in browser DevTools | Proxy through backend |
| `dangerouslySetInnerHTML` with raw data | XSS risk | Let React escape strings, or use DOMPurify |
| Commit `.env` to git | Exposes secrets to the world | `.gitignore` + `.env.example` |
| Skip rate limiting | One user can exhaust your API | Use `slowapi` or similar |