# backend/app/database.py
import os
import sqlite3
from contextlib import contextmanager
from typing import Optional

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

_DEFAULT_DB = os.path.join(os.path.dirname(__file__), "..", "cortex", "models", "potholes.db")
DB_PATH = os.getenv("DATABASE_URL", f"sqlite:///{_DEFAULT_DB}").replace("sqlite:///", "")

# Columns we expose from the potholes table — never SELECT *
POTHOLE_COLS = """unique_key, latitude, longitude, borough, street_name,
    descriptor, status, created_date, closed_date,
    age_days, risk_score, urgency_label, urgency_tier, fix_days_estimate,
    traffic_volume, aadt, nearby_crashes, pavement_crash_nearby,
    prob_low, prob_medium, prob_high, prob_critical, scored_at"""


# Columns we expose from the alerts table
ALERT_COLS = "id, pothole_id, urgency, risk_score, borough, street_name, message, sent_at, delivered"


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
                prob_critical         REAL
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
        """)
        conn.commit()
        print("Database initialized successfully")


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
            values = [row.get(c) for c in cols]
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