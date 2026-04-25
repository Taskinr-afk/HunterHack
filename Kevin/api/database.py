"""
SQLite database layer for PotholeIQ.

Stores pre-scored pothole records so the API can serve map data
without hitting the ML model on every request.

Tables:
  potholes  — one row per pothole, enriched + scored
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import pandas as pd

DB_PATH = Path(__file__).parent.parent / "ml" / "models" / "potholes.db"


# ── Schema ─────────────────────────────────────────────────────────────────────

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS potholes (
    unique_key              TEXT PRIMARY KEY,
    created_date            TEXT,
    closed_date             TEXT,
    status                  TEXT,
    descriptor              TEXT,
    borough                 TEXT,
    street_name             TEXT,
    latitude                REAL,
    longitude               REAL,
    age_days                REAL,
    traffic_volume          REAL,
    aadt                    REAL,
    nearby_crashes          INTEGER DEFAULT 0,
    pavement_crash_nearby   INTEGER DEFAULT 0,
    risk_score              REAL,
    urgency_tier            INTEGER,
    urgency_label           TEXT,
    fix_days_estimate       INTEGER,
    prob_low                REAL,
    prob_medium             REAL,
    prob_high               REAL,
    prob_critical           REAL,
    scored_at               TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_borough     ON potholes(borough);
CREATE INDEX IF NOT EXISTS idx_status      ON potholes(status);
CREATE INDEX IF NOT EXISTS idx_urgency     ON potholes(urgency_tier);
CREATE INDEX IF NOT EXISTS idx_risk        ON potholes(risk_score);
CREATE INDEX IF NOT EXISTS idx_location    ON potholes(latitude, longitude);
"""


# ── Connection helper ──────────────────────────────────────────────────────────

@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(_CREATE_SQL)


# ── Write ──────────────────────────────────────────────────────────────────────

def upsert_potholes(df: pd.DataFrame) -> int:
    """Insert or replace all rows from a scored DataFrame. Returns row count."""
    _COLS = [
        "unique_key", "created_date", "closed_date", "status",
        "descriptor", "borough", "street_name", "latitude", "longitude",
        "age_days", "traffic_volume", "aadt", "nearby_crashes",
        "pavement_crash_nearby", "risk_score", "urgency_tier", "urgency_label",
        "fix_days_estimate", "prob_low", "prob_medium", "prob_high", "prob_critical",
    ]

    # keep only columns that exist in the DataFrame
    cols = [c for c in _COLS if c in df.columns]
    tmp  = df[cols].copy()
    # SQLite doesn't accept Timestamp objects — convert to ISO strings
    for col in ("created_date", "closed_date"):
        if col in tmp.columns:
            tmp[col] = tmp[col].astype(str).replace("NaT", None)
    rows = tmp.where(tmp.notna(), other=None).to_dict(orient="records")

    placeholders = ", ".join(f":{c}" for c in cols)
    col_list     = ", ".join(cols)
    sql = f"INSERT OR REPLACE INTO potholes ({col_list}) VALUES ({placeholders})"

    with get_conn() as conn:
        conn.executemany(sql, rows)
    return len(rows)


# ── Read ───────────────────────────────────────────────────────────────────────

def query_potholes(
    status:     str | None = None,
    borough:    str | None = None,
    min_risk:   float      = 0.0,
    urgency:    str | None = None,
    limit:      int        = 5_000,
) -> list[dict]:
    conditions = ["1=1"]
    params: list = []

    if status:
        conditions.append("status = ?")
        params.append(status)
    if borough:
        conditions.append("UPPER(borough) = UPPER(?)")
        params.append(borough)
    if min_risk > 0:
        conditions.append("risk_score >= ?")
        params.append(min_risk)
    if urgency:
        conditions.append("UPPER(urgency_label) = UPPER(?)")
        params.append(urgency)

    where = " AND ".join(conditions)
    sql   = f"SELECT * FROM potholes WHERE {where} ORDER BY risk_score DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [dict(r) for r in rows]


def get_stats() -> dict:
    sql = """
    SELECT
        COUNT(*)                                          AS total,
        SUM(CASE WHEN status='Open' THEN 1 ELSE 0 END)  AS open_count,
        SUM(CASE WHEN urgency_tier=3 THEN 1 ELSE 0 END) AS critical,
        SUM(CASE WHEN urgency_tier=2 THEN 1 ELSE 0 END) AS high,
        SUM(CASE WHEN urgency_tier=1 THEN 1 ELSE 0 END) AS medium,
        SUM(CASE WHEN urgency_tier=0 THEN 1 ELSE 0 END) AS low,
        ROUND(AVG(risk_score), 2)                        AS avg_risk_score
    FROM potholes
    """
    borough_sql = """
    SELECT
        borough,
        COUNT(*)                                          AS total,
        SUM(CASE WHEN status='Open' THEN 1 ELSE 0 END)  AS open_count,
        SUM(CASE WHEN urgency_tier=3 THEN 1 ELSE 0 END) AS critical_count,
        SUM(CASE WHEN urgency_tier=2 THEN 1 ELSE 0 END) AS high_count,
        ROUND(AVG(risk_score), 2)                        AS avg_risk_score,
        ROUND(AVG(age_days), 1)                          AS avg_age_days
    FROM potholes
    GROUP BY borough
    ORDER BY avg_risk_score DESC
    """
    with get_conn() as conn:
        summary     = dict(conn.execute(sql).fetchone())
        by_borough  = [dict(r) for r in conn.execute(borough_sql).fetchall()]

    summary["by_borough"] = by_borough
    return summary
