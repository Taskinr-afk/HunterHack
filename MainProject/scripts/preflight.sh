#!/usr/bin/env bash
#
# PotholeIQ — Demo Day Preflight Checklist
#
# Usage:
#   bash scripts/preflight.sh          # full check + start
#   bash scripts/preflight.sh --check  # check only, don't start servers
#   bash scripts/preflight.sh --seed   # force re-seed database
#
set -euo pipefail

# ── Colors ──────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Config ──────────────────────────────────────────────────────────────────────
BACKEND_PORT=8000
FRONTEND_PORT=5173
BACKEND_URL="http://localhost:${BACKEND_PORT}"
FRONTEND_URL="http://localhost:${FRONTEND_PORT}"
DB_PATH="MainProject/Backend/cortex/models/potholes.db"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FORCE_SEED=false
CHECK_ONLY=false

# Prefer venv if it exists, otherwise fall back to system python3
VENV_DIR="${PROJECT_ROOT}/MainProject/Backend/.venv"
if [ -f "${VENV_DIR}/bin/python3" ]; then
  PYTHON="${VENV_DIR}/bin/python3"
  PIP="${VENV_DIR}/bin/pip"
else
  # Try project root venv
  VENV_DIR="${PROJECT_ROOT}/.venv"
  if [ -f "${VENV_DIR}/bin/python3" ]; then
    PYTHON="${VENV_DIR}/bin/python3"
    PIP="${VENV_DIR}/bin/pip"
  else
    PYTHON="$(command -v python3)"
    PIP="$(command -v pip3 2>/dev/null || echo pip3)"
  fi
fi

# ── Parse args ──────────────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --check)  CHECK_ONLY=true ;;
    --seed)   FORCE_SEED=true ;;
    --help|-h)
      echo "Usage: bash scripts/preflight.sh [--check] [--seed]"
      echo "  --check   Run checks only, don't start servers"
      echo "  --seed    Force re-seed the database"
      exit 0 ;;
  esac
done

cd "$PROJECT_ROOT"

# ── Helpers ─────────────────────────────────────────────────────────────────────
pass()  { echo -e "  ${GREEN}✓${NC} $1"; }
fail()  { echo -e "  ${RED}✗${NC} $1"; }
warn()  { echo -e "  ${YELLOW}!${NC} $1"; }
info()  { echo -e "  ${CYAN}→${NC} $1"; }
step()  { echo -e "\n${CYAN}▸ $1${NC}"; }

# ── Step 1: Check dependencies ────────────────────────────────────────────────
step "Checking dependencies"

if command -v python3 &>/dev/null; then
  pass "python3 found: $PYTHON"
else
  fail "python3 not found — install Python 3.10+"
  exit 1
fi

if command -v node &>/dev/null; then
  pass "node found: $(node --version)"
else
  fail "node not found — install Node.js 18+"
  exit 1
fi

if command -v npm &>/dev/null; then
  pass "npm found: $(npm --version)"
else
  fail "npm not found"
  exit 1
fi

# ── Step 2: Set up venv if needed ──────────────────────────────────────────────
step "Checking Python environment"

if [ ! -f "${VENV_DIR}/bin/python3" ]; then
  info "Creating virtual environment at ${VENV_DIR}..."
  python3 -m venv "${VENV_DIR}"
  VENV_DIR="${VENV_DIR}"
  PYTHON="${VENV_DIR}/bin/python3"
  PIP="${VENV_DIR}/bin/pip"
  pass "Virtual environment created"
else
  pass "Virtual environment exists at ${VENV_DIR}"
fi

# ── Step 3: Install Python dependencies ────────────────────────────────────────
step "Checking Python packages"

MISSING_PY=()
for pkg in fastapi uvicorn pandas numpy xgboost scikit-learn joblib pyarrow requests slowapi python-dotenv pydantic httpx; do
  if $PYTHON -c "import ${pkg//-/_}" &>/dev/null; then
    pass "$pkg"
  else
    fail "$pkg missing"
    MISSING_PY+=("$pkg")
  fi
done

if [ ${#MISSING_PY[@]} -gt 0 ]; then
  info "Installing missing packages..."
  $PIP install -r MainProject/Backend/requirements.txt
  pass "Dependencies installed"
fi

# ── Step 4: Install frontend dependencies ──────────────────────────────────────
step "Checking frontend dependencies"

if [ -d "MainProject/Frontend/node_modules" ]; then
  pass "node_modules exists"
else
  info "Installing frontend dependencies..."
  (cd MainProject/Frontend && npm install)
  pass "Frontend dependencies installed"
fi

# ── Step 5: Database check and seed ─────────────────────────────────────────────
step "Checking database"

DB_EXISTS=false
if [ -f "$DB_PATH" ]; then
  DB_EXISTS=true
  ROW_COUNT=$($PYTHON -c "
import sqlite3
conn = sqlite3.connect('${DB_PATH}')
cur = conn.execute('SELECT COUNT(*) FROM potholes')
print(cur.fetchone()[0])
conn.close()
" 2>/dev/null || echo "0")

  if [ "$ROW_COUNT" -gt 0 ]; then
    pass "Database has $ROW_COUNT pothole records"
  else
    warn "Database exists but is empty — will seed"
    FORCE_SEED=true
  fi
else
  warn "Database file not found at $DB_PATH — will create and seed"
  # Ensure the directory exists
  mkdir -p "$(dirname "$DB_PATH")"
  FORCE_SEED=true
fi

if [ "$FORCE_SEED" = true ]; then
  info "Seeding database with 500 demo records..."
  PYTHONPATH=. $PYTHON -c "
from Backend.app.database import init_db, get_conn
from Backend.app.seed import seed_demo_data
init_db()
# Clear existing data first for clean re-seed
with get_conn() as conn:
    conn.execute('DELETE FROM potholes')
    conn.execute('DELETE FROM alerts')
seed_demo_data(500)
with get_conn() as conn:
    count = conn.execute('SELECT COUNT(*) FROM potholes').fetchone()[0]
    print(f'  Seeded {count} pothole records')
"
  pass "Database seeded"
fi

# ── Step 6: Health check — start backend if needed ────────────────────────────
step "Checking backend API"

BACKEND_RUNNING=false
if curl -sf "${BACKEND_URL}/" &>/dev/null; then
  BACKEND_RUNNING=true
  pass "Backend already running on port ${BACKEND_PORT}"
else
  if [ "$CHECK_ONLY" = true ]; then
    warn "Backend not running — skipping start (--check mode)"
  else
    info "Starting backend server..."
    PYTHONPATH=. $PYTHON -m uvicorn Backend.app.main:app --port "${BACKEND_PORT}" &
    BACKEND_PID=$!
    echo "$BACKEND_PID" > /tmp/potholeiq_backend.pid

    # Wait for backend to be ready
    for i in $(seq 1 30); do
      if curl -sf "${BACKEND_URL}/" &>/dev/null; then
        BACKEND_RUNNING=true
        break
      fi
      sleep 1
    done

    if [ "$BACKEND_RUNNING" = true ]; then
      pass "Backend started (PID: $BACKEND_PID)"
    else
      fail "Backend failed to start within 30 seconds"
      exit 1
    fi
  fi
fi

# ── Step 7: Verify API endpoints ────────────────────────────────────────────────
step "Verifying API endpoints"

if [ "$BACKEND_RUNNING" = true ]; then
  # Health check
  HEALTH=$(curl -sf "${BACKEND_URL}/" 2>/dev/null)
  if [ -n "$HEALTH" ]; then
    pass "GET / — health check OK"
  else
    fail "GET / — no response"
  fi

  # GeoJSON endpoint
  GEOJSON_COUNT=$(curl -sf "${BACKEND_URL}/potholes/geojson?limit=5" 2>/dev/null | $PYTHON -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(len(data.get('features', [])))
except:
    print('0')
" 2>/dev/null || echo "0")

  if [ "$GEOJSON_COUNT" -gt 0 ]; then
    pass "GET /potholes/geojson — ${GEOJSON_COUNT} features returned"
  else
    fail "GET /potholes/geojson — 0 features (database may be empty)"
  fi

  # Stats endpoint
  STATS=$(curl -sf "${BACKEND_URL}/api/stats/summary" 2>/dev/null)
  if [ -n "$STATS" ]; then
    TOTAL_OPEN=$(echo "$STATS" | $PYTHON -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('total_open', 0))
except:
    print('error')
" 2>/dev/null || echo "error")
    pass "GET /api/stats/summary — total_open: ${TOTAL_OPEN}"
  else
    fail "GET /api/stats/summary — no response"
  fi

  # Pothole detail endpoint
  FIRST_KEY=$(curl -sf "${BACKEND_URL}/potholes/geojson?limit=1" 2>/dev/null | $PYTHON -c "
import sys, json
try:
    data = json.load(sys.stdin)
    props = data['features'][0]['properties']
    print(props['unique_key'])
except:
    print('')
" 2>/dev/null || echo "")

  if [ -n "$FIRST_KEY" ]; then
    DETAIL=$(curl -sf "${BACKEND_URL}/api/potholes/${FIRST_KEY}" 2>/dev/null)
    if [ -n "$DETAIL" ]; then
      pass "GET /api/potholes/${FIRST_KEY} — detail endpoint OK"
    else
      fail "GET /api/potholes/${FIRST_KEY} — no response"
    fi
  else
    warn "Could not fetch pothole detail (no keys returned)"
  fi
else
  warn "Backend not running — skipping endpoint verification"
fi

# ── Step 8: Start frontend if needed ────────────────────────────────────────────
step "Checking frontend dev server"

FRONTEND_RUNNING=false
if curl -sf "${FRONTEND_URL}" &>/dev/null; then
  FRONTEND_RUNNING=true
  pass "Frontend already running on port ${FRONTEND_PORT}"
else
  if [ "$CHECK_ONLY" = true ]; then
    warn "Frontend not running — skipping start (--check mode)"
  else
    info "Starting frontend dev server..."
    (cd MainProject/Frontend && npm run dev) &
    FRONTEND_PID=$!
    echo "$FRONTEND_PID" > /tmp/potholeiq_frontend.pid

    for i in $(seq 1 30); do
      if curl -sf "${FRONTEND_URL}" &>/dev/null; then
        FRONTEND_RUNNING=true
        break
      fi
      sleep 1
    done

    if [ "$FRONTEND_RUNNING" = true ]; then
      pass "Frontend started (PID: $FRONTEND_PID)"
    else
      warn "Frontend not yet responding (may still be compiling — try ${FRONTEND_URL} in browser)"
    fi
  fi
fi

# ── Summary ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  PotholeIQ — Preflight Summary${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"

if [ "$BACKEND_RUNNING" = true ]; then
  echo -e "  ${GREEN}Backend:${NC}  ${BACKEND_URL}"
else
  echo -e "  ${RED}Backend:${NC}  not running"
fi

if [ "$FRONTEND_RUNNING" = true ]; then
  echo -e "  ${GREEN}Frontend:${NC} ${FRONTEND_URL}"
else
  echo -e "  ${YELLOW}Frontend:${NC} not running (may still be starting)"
fi

echo -e "  ${GREEN}API Docs:${NC}  ${BACKEND_URL}/docs"

if [ "$CHECK_ONLY" = false ]; then
  echo ""
  echo -e "  ${CYAN}Open your browser to:${NC} ${FRONTEND_URL}"
  echo ""
  echo -e "  ${YELLOW}To stop servers:${NC}"
  echo -e "    kill \$(cat /tmp/potholeiq_backend.pid) 2>/dev/null"
  echo -e "    kill \$(cat /tmp/potholeiq_frontend.pid) 2>/dev/null"
fi

echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"