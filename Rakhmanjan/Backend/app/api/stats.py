"""
GET /api/stats/summary    borough-level aggregated stats
GET /api/stats/timeline   weekly opened vs closed counts
"""

from fastapi import APIRouter
from ..database import get_conn
from ..schemas import StatsSummary, StatsBoroughEntry, TimelinePoint

router = APIRouter(prefix="/api/stats", tags=["stats"])

_BOROUGHS = ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN ISLAND"]


@router.get("/summary", response_model=StatsSummary)
def get_stats_summary():
    with get_conn() as conn:
        total_open = conn.execute(
            "SELECT COUNT(*) FROM potholes WHERE status = 'Open'"
        ).fetchone()[0]

        total_closed = conn.execute(
            "SELECT COUNT(*) FROM potholes WHERE status = 'Closed'"
        ).fetchone()[0]

        avg_days = conn.execute(
            "SELECT AVG(age_days) FROM potholes WHERE status = 'Open'"
        ).fetchone()[0] or 0.0

        by_borough: dict[str, BoroughStats] = {}
        for borough in _BOROUGHS:
            open_c = conn.execute(
                "SELECT COUNT(*) FROM potholes WHERE UPPER(borough)=? AND status='Open'",
                (borough,)
            ).fetchone()[0]

            closed_c = conn.execute(
                "SELECT COUNT(*) FROM potholes WHERE UPPER(borough)=? AND status='Closed'",
                (borough,)
            ).fetchone()[0]

            avg_b = conn.execute(
                "SELECT AVG(age_days) FROM potholes WHERE UPPER(borough)=? AND status='Open'",
                (borough,)
            ).fetchone()[0] or 0.0

            crashes = conn.execute(
                "SELECT SUM(nearby_crashes) FROM potholes WHERE UPPER(borough)=?",
                (borough,)
            ).fetchone()[0] or 0

            by_borough[borough.title()] = StatsBoroughEntry(
                open_count       = open_c,
                closed_count     = closed_c,
                avg_days_open    = round(avg_b, 1),
                total_collisions = int(crashes),
            )

    return StatsSummary(
        total_open    = total_open,
        total_closed  = total_closed,
        avg_days_open = round(avg_days, 1),
        by_borough    = by_borough,
    )


@router.get("/timeline", response_model=list[TimelinePoint])
def get_stats_timeline():
    with get_conn() as conn:
        opened = conn.execute("""
            SELECT strftime('%Y-%W', created_date) AS week, COUNT(*) AS cnt
            FROM potholes
            WHERE created_date > '2024-01-01'
            GROUP BY week ORDER BY week
        """).fetchall()

        closed = conn.execute("""
            SELECT strftime('%Y-%W', closed_date) AS week, COUNT(*) AS cnt
            FROM potholes
            WHERE closed_date IS NOT NULL AND closed_date > '2024-01-01'
            GROUP BY week ORDER BY week
        """).fetchall()

    closed_map = {r["week"]: r["cnt"] for r in closed}
    return [
        TimelinePoint(
            week   = r["week"],
            opened = r["cnt"],
            closed = closed_map.get(r["week"], 0),
        )
        for r in opened
    ]
