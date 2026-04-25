# backend/app/database.py
import sqlite3
from contextlib import contextmanager
import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "potholes.db"

# --- Database connection ---
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Returns dict-like rows
    try:
        yield conn
    finally:
        conn.close()

# --- Create tables if they don't exist ---
def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS potholes (
                id              TEXT PRIMARY KEY,
                latitude        REAL NOT NULL,
                longitude       REAL NOT NULL,
                borough         TEXT,
                zip_code        TEXT,
                descriptor      TEXT,
                status          TEXT,
                created_date    TEXT,
                closed_date     TEXT,
                days_open       INTEGER DEFAULT 0,
                impact_score    REAL,
                accident_risk   TEXT,
                predicted_repair_days INTEGER,
                nearby_collision_count INTEGER DEFAULT 0,
                traffic_volume  INTEGER
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                pothole_id      TEXT NOT NULL,
                message         TEXT,
                sent_at         TEXT,
                status          TEXT DEFAULT 'pending'
            );
        """)
        conn.commit()
        print("Database initialized successfully")

# --- Get all potholes (safe parameterized queries) ---
def get_potholes(borough: str = None, status: str = None, limit: int = 100, offset: int = 0):
    with get_db() as conn:
        query = """
            SELECT id, latitude, longitude, borough, status,
                   created_date, closed_date, days_open, descriptor,
                   impact_score, accident_risk, predicted_repair_days,
                   nearby_collision_count, traffic_volume
            FROM potholes
            WHERE 1=1
        """
        params = []

        if borough:
            query += " AND borough = ?"       # ? placeholder = SAFE from SQL injection
            params.append(borough)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_date DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

# --- Get single pothole by ID ---
def get_pothole_by_id(pothole_id: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM potholes WHERE id = ?",  # SAFE
            (pothole_id,)
        ).fetchone()
        return dict(row) if row else None

# --- Save alert to database ---
def save_alert(pothole_id: str, message: str, status: str = "pending"):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO alerts (pothole_id, message, sent_at, status) VALUES (?, ?, datetime('now'), ?)",
            (pothole_id, message, status)   # SAFE
        )
        conn.commit()

# --- Get alert history ---
def get_alert_history():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM alerts ORDER BY sent_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]