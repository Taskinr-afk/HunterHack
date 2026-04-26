# backend/app/database.py
import os
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import pandas as pd

load_dotenv()

_APP_DIR = Path(__file__).resolve().parent
_DEFAULT_DB = (_APP_DIR / ".." / "cortex" / "models" / "potholes.db").resolve()
_TMP_DB = Path("/tmp/potholeiq/potholes.db")


def _resolve_db_path() -> str:
    configured = os.getenv("DATABASE_URL")
    if configured:
        return configured.replace("sqlite:///", "")

    if os.getenv("VERCEL"):
        _TMP_DB.parent.mkdir(parents=True, exist_ok=True)
        if not _TMP_DB.exists() and _DEFAULT_DB.exists():
            shutil.copyfile(_DEFAULT_DB, _TMP_DB)
        return str(_TMP_DB)

    return str(_DEFAULT_DB)


DB_PATH = _resolve_db_path()

# Columns we expose from the potholes table — never SELECT *
POTHOLE_COLS = """unique_key, latitude, longitude, borough, street_name,
    descriptor, status, created_date, closed_date,
    age_days, risk_score, urgency_label, urgency_tier, fix_days_estimate,
    traffic_volume, aadt, nearby_crashes, pavement_crash_nearby,
    prob_low, prob_medium, prob_high, prob_critical"""


# Columns we expose from the alerts table
ALERT_COLS = "id, pothole_id, urgency, risk_score, borough, street_name, message, sent_at, delivered"

# Columns we expose from the reports table
REPORT_COLS = """id, latitude, longitude, borough, street_name,
    descriptor, reporter_name, reporter_email, image_url,
    status, pothole_key, created_at, verified_at"""

# Borough bounding boxes for coordinate inference
BOROUGH_BOUNDS = {
    "MANHATTAN":     ((40.700, 40.880), (-74.020, -73.910)),
    "BROOKLYN":      ((40.570, 40.740), (-74.040, -73.830)),
    "QUEENS":        ((40.540, 40.800), (-73.960, -73.700)),
    "BRONX":         ((40.785, 40.920), (-73.930, -73.760)),
    "STATEN ISLAND": ((40.490, 40.650), (-74.250, -74.080)),
}


def infer_borough(lat: float, lon: float) -> str:
    """Infer the NYC borough from coordinates using bounding boxes."""
    for borough, ((lat_lo, lat_hi), (lon_lo, lon_hi)) in BOROUGH_BOUNDS.items():
        if lat_lo <= lat <= lat_hi and lon_lo <= lon <= lon_hi:
            return borough
    return "UNKNOWN"

POTHOLE_OPTIONAL_COLUMNS = {
    "zip_code": "TEXT",
    "location_type": "TEXT",
    "age_days": "REAL DEFAULT 0",
    "risk_score": "REAL DEFAULT 0",
    "urgency_label": "TEXT DEFAULT 'Low'",
    "urgency_tier": "INTEGER DEFAULT 0",
    "fix_days_estimate": "INTEGER DEFAULT 30",
    "traffic_volume": "REAL",
    "aadt": "REAL",
    "nearby_crashes": "INTEGER DEFAULT 0",
    "pavement_crash_nearby": "INTEGER DEFAULT 0",
    "prob_low": "REAL",
    "prob_medium": "REAL",
    "prob_high": "REAL",
    "prob_critical": "REAL",
    "scored_at": "TEXT",
}

ALERT_OPTIONAL_COLUMNS = {
    "status": "TEXT DEFAULT 'pending'",
    "urgency": "TEXT",
    "risk_score": "REAL DEFAULT 0",
    "borough": "TEXT",
    "street_name": "TEXT",
    "delivered": "INTEGER DEFAULT 0",
}


# ── Database connection ────────────────────────────────────────────────────────

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# Alias used by route modules
get_conn = get_db


# ── Schema ─────────────────────────────────────────────────────────────────────

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS potholes (
                unique_key            TEXT PRIMARY KEY,
                latitude              REAL NOT NULL,
                longitude             REAL NOT NULL,
                borough               TEXT,
                street_name           TEXT,
                zip_code              TEXT,
                descriptor            TEXT,
                status                TEXT,
                created_date          TEXT,
                closed_date           TEXT,
                location_type         TEXT,
                age_days              REAL DEFAULT 0,
                risk_score            REAL DEFAULT 0,
                urgency_label         TEXT DEFAULT 'Low',
                urgency_tier          INTEGER DEFAULT 0,
                fix_days_estimate     INTEGER DEFAULT 30,
                traffic_volume        REAL,
                aadt                  REAL,
                nearby_crashes        INTEGER DEFAULT 0,
                pavement_crash_nearby INTEGER DEFAULT 0,
                prob_low              REAL,
                prob_medium           REAL,
                prob_high             REAL,
                prob_critical         REAL,
                scored_at             TEXT
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                pothole_id   TEXT NOT NULL,
                message      TEXT,
                sent_at      TEXT,
                status       TEXT DEFAULT 'pending',
                urgency      TEXT,
                risk_score   REAL DEFAULT 0,
                borough      TEXT,
                street_name  TEXT,
                delivered    INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS reports (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                latitude        REAL NOT NULL,
                longitude       REAL NOT NULL,
                borough         TEXT,
                street_name     TEXT,
                descriptor      TEXT,
                reporter_name   TEXT,
                reporter_email  TEXT,
                image_url       TEXT,
                status          TEXT DEFAULT 'unverified',
                pothole_key     TEXT,
                created_at      TEXT NOT NULL,
                verified_at     TEXT
            );
        """)

        pothole_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(potholes)").fetchall()
        }
        for column, definition in POTHOLE_OPTIONAL_COLUMNS.items():
            if column not in pothole_columns:
                conn.execute(f"ALTER TABLE potholes ADD COLUMN {column} {definition}")

        alert_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(alerts)").fetchall()
        }
        for column, definition in ALERT_OPTIONAL_COLUMNS.items():
            if column not in alert_columns:
                conn.execute(f"ALTER TABLE alerts ADD COLUMN {column} {definition}")

        conn.execute("""
            UPDATE potholes
            SET street_name = NULL
            WHERE LOWER(TRIM(COALESCE(street_name, ''))) IN ('nan', 'none', 'null', '<na>')
        """)
        conn.execute("""
            UPDATE potholes
            SET borough = 'UNKNOWN'
            WHERE LOWER(TRIM(COALESCE(borough, ''))) IN ('', 'nan', 'none', 'null', '<na>')
        """)

        conn.commit()
        print("Database initialized successfully")


def _to_sql_value(value):
    if value is None:
        return None

    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.lower() in {"nan", "none", "null", "<na>"}:
            return None
        return cleaned

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    item = getattr(value, "item", None)
    if callable(item):
        try:
            return item()
        except Exception:
            pass

    try:
        if value != value:
            return None
    except Exception:
        pass

    return value


# ── Pothole queries ───────────────────────────────────────────────────────────

def query_potholes(
    status: Optional[str] = None,
    borough: Optional[str] = None,
    min_risk: float = 0.0,
    urgency: Optional[str] = None,
    limit: int = 5000,
) -> list[dict]:
    """Return pothole rows matching filters (used by GeoJSON endpoint)."""
    with get_db() as conn:
        query = f"SELECT {POTHOLE_COLS} FROM potholes WHERE 1=1"
        params: list = []

        if status:
            query += " AND LOWER(status) = LOWER(?)"
            params.append(status)
        if borough:
            query += " AND UPPER(borough) = UPPER(?)"
            params.append(borough)
        if min_risk > 0:
            query += " AND risk_score >= ?"
            params.append(min_risk)
        if urgency:
            query += " AND LOWER(urgency_label) = LOWER(?)"
            params.append(urgency)

        query += " ORDER BY risk_score DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def get_pothole_by_key(unique_key: str) -> Optional[dict]:
    """Return a single pothole by unique_key."""
    with get_db() as conn:
        row = conn.execute(
            f"SELECT {POTHOLE_COLS} FROM potholes WHERE unique_key = ?",
            (unique_key,),
        ).fetchone()
        return dict(row) if row else None


def upsert_potholes(df: pd.DataFrame) -> int:
    """Insert or update pothole rows from the scored ML DataFrame."""
    cols = [
        "unique_key", "latitude", "longitude", "borough", "street_name",
        "descriptor", "status", "created_date", "closed_date", "location_type",
        "age_days", "risk_score", "urgency_label", "urgency_tier", "fix_days_estimate",
        "traffic_volume", "aadt", "nearby_crashes", "pavement_crash_nearby",
        "prob_low", "prob_medium", "prob_high", "prob_critical",
    ]
    # Fill missing columns with defaults
    for c in cols:
        if c not in df.columns:
            df[c] = None

    with get_db() as conn:
        count = 0
        for _, row in df.iterrows():
            values = [_to_sql_value(row.get(c)) for c in cols]
            placeholders = ", ".join(["?"] * len(cols))
            col_names = ", ".join(cols)
            update_sets = ", ".join(f"{c}=excluded.{c}" for c in cols if c != "unique_key")
            sql = f"INSERT INTO potholes ({col_names}) VALUES ({placeholders}) ON CONFLICT(unique_key) DO UPDATE SET {update_sets}"
            conn.execute(sql, values)
            count += 1
        conn.commit()
    return count


# ── Stats ──────────────────────────────────────────────────────────────────────

def get_stats() -> dict:
    """Aggregate stats for the /stats endpoint."""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM potholes").fetchone()[0]
        open_c = conn.execute("SELECT COUNT(*) FROM potholes WHERE LOWER(status)='open'").fetchone()[0]
        critical = conn.execute("SELECT COUNT(*) FROM potholes WHERE urgency_label='Critical'").fetchone()[0]
        high = conn.execute("SELECT COUNT(*) FROM potholes WHERE urgency_label='High'").fetchone()[0]
        medium = conn.execute("SELECT COUNT(*) FROM potholes WHERE urgency_label='Medium'").fetchone()[0]
        low = conn.execute("SELECT COUNT(*) FROM potholes WHERE urgency_label='Low'").fetchone()[0]
        avg_risk = conn.execute("SELECT AVG(risk_score) FROM potholes WHERE risk_score IS NOT NULL").fetchone()[0] or 0.0

        by_borough = []
        for b in ("MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN ISLAND"):
            b_total = conn.execute("SELECT COUNT(*) FROM potholes WHERE UPPER(borough)=?", (b,)).fetchone()[0]
            b_open = conn.execute("SELECT COUNT(*) FROM potholes WHERE UPPER(borough)=? AND LOWER(status)='open'", (b,)).fetchone()[0]
            b_critical = conn.execute("SELECT COUNT(*) FROM potholes WHERE UPPER(borough)=? AND urgency_label='Critical'", (b,)).fetchone()[0]
            b_high = conn.execute("SELECT COUNT(*) FROM potholes WHERE UPPER(borough)=? AND urgency_label='High'", (b,)).fetchone()[0]
            b_avg = conn.execute("SELECT AVG(risk_score) FROM potholes WHERE UPPER(borough)=? AND risk_score IS NOT NULL", (b,)).fetchone()[0] or 0.0
            b_age = conn.execute("SELECT AVG(age_days) FROM potholes WHERE UPPER(borough)=? AND LOWER(status)='open'", (b,)).fetchone()[0] or 0.0
            by_borough.append({
                "borough": b.title(),
                "total": b_total,
                "open_count": b_open,
                "critical_count": b_critical,
                "high_count": b_high,
                "avg_risk_score": round(b_avg, 1),
                "avg_age_days": round(b_age, 1),
            })

    return {
        "total": total,
        "open_count": open_c,
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
        "avg_risk_score": round(avg_risk, 1),
        "by_borough": by_borough,
    }


# ── Alert queries ─────────────────────────────────────────────────────────────

def insert_alert(
    pothole_id: str,
    message: str,
    urgency: str = "",
    risk_score: float = 0,
    borough: str = "",
    street_name: str = "",
    delivered: bool = False,
    status: str = "pending",
) -> int:
    """Insert an alert and return its id."""
    with get_db() as conn:
        cur = conn.execute(
            f"INSERT INTO alerts (pothole_id, urgency, risk_score, borough, street_name, message, delivered) "
            f"VALUES (?, ?, ?, ?, ?, ?, ?)",
            (pothole_id, urgency, risk_score, borough, street_name, message, 1 if delivered else 0),
        )
        conn.commit()
        return cur.lastrowid


def get_alert_history(limit: int = 100) -> list[dict]:
    """Return recent alerts, most recent first."""
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT {ALERT_COLS} FROM alerts ORDER BY sent_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_high_risk_unalerted(min_risk: float = 75.0, limit: int = 50) -> list[dict]:
    """Return high-risk potholes that haven't been alerted yet."""
    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT {POTHOLE_COLS} FROM potholes
            WHERE risk_score >= ?
              AND LOWER(status) = 'open'
              AND unique_key NOT IN (
                  SELECT pothole_id FROM alerts WHERE delivered = 1
              )
            ORDER BY risk_score DESC
            LIMIT ?
            """,
            (min_risk, limit),
        ).fetchall()
        return [dict(row) for row in rows]


# ── Report queries ──────────────────────────────────────────────────────────

def insert_report(
    latitude: float, longitude: float,
    borough: str, street_name: str, descriptor: str,
    reporter_name: str, reporter_email: str, image_url: str,
    pothole_key: str,
) -> int:
    """Insert a citizen report and return its id."""
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO reports
               (latitude, longitude, borough, street_name, descriptor,
                reporter_name, reporter_email, image_url, status,
                pothole_key, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (latitude, longitude, borough, street_name, descriptor,
             reporter_name, reporter_email, image_url, "unverified",
             pothole_key, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return cur.lastrowid


def insert_unverified_pothole(
    unique_key: str, latitude: float, longitude: float,
    borough: str, street_name: str, descriptor: str,
) -> None:
    """Insert an unverified pothole into the potholes table so it appears on the map."""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO potholes
               (unique_key, latitude, longitude, borough, street_name,
                descriptor, status, created_date, age_days, risk_score,
                urgency_label, urgency_tier, fix_days_estimate,
                nearby_crashes, prob_low, prob_medium, prob_high, prob_critical)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (unique_key, latitude, longitude, borough, street_name,
             descriptor, "unverified",
             datetime.now(timezone.utc).isoformat(),
             0, 0, "Unverified", 0, 30,
             0, 0.25, 0.25, 0.25, 0.25),
        )
        conn.commit()


def get_unverified_reports(limit: int = 200) -> list[dict]:
    """Return unverified citizen reports, most recent first."""
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT {REPORT_COLS} FROM reports WHERE status = 'unverified' ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
