"""SQLite-backed cache of NSE index trend data (see nse_client.get_all_indices),
refreshed at most daily. Only the broad NIFTY 50 trend is currently used
by ipo_potential_service.py as a general "market conditions" factor -- a
given IPO can't be reliably mapped to a specific sector with any data
source confirmed so far (see feature/ipo-potential-score's Phase 0
notes), so per-sector rows are stored for future use but not yet consumed.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from app.db.database import get_connection


@dataclass
class MarketTrend:
    index_symbol: str
    percent_change_1d: float | None
    percent_change_30d: float | None
    recorded_at: str


def upsert(index_symbol: str, percent_change_1d: float | None, percent_change_30d: float | None) -> None:
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO market_trend_cache (id, index_symbol, percent_change_1d, percent_change_30d, recorded_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                percent_change_1d = excluded.percent_change_1d,
                percent_change_30d = excluded.percent_change_30d,
                recorded_at = excluded.recorded_at
            """,
            (index_symbol, index_symbol, percent_change_1d, percent_change_30d, now),
        )
        conn.commit()
    finally:
        conn.close()


def get(index_symbol: str) -> MarketTrend | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM market_trend_cache WHERE id = ?", (index_symbol,)
        ).fetchone()
        return (
            MarketTrend(
                index_symbol=row["index_symbol"],
                percent_change_1d=row["percent_change_1d"],
                percent_change_30d=row["percent_change_30d"],
                recorded_at=row["recorded_at"],
            )
            if row
            else None
        )
    finally:
        conn.close()
