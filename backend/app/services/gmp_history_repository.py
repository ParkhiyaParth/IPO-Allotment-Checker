"""Bounded per-IPO history of GMP% readings, used to detect momentum swings
(ipo_catalog_service._detect_gmp_swing). Capped at _MAX_SAMPLES_PER_CATALOG
rows per catalog_id so this can't grow unbounded on the 1GB production box --
pruned on every insert.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from app.db.database import get_connection

_MAX_SAMPLES_PER_CATALOG = 10


@dataclass
class GmpSample:
    catalog_id: str
    gmp_percent: float | None
    recorded_at: str


def append(catalog_id: str, gmp_percent: float | None) -> None:
    if gmp_percent is None:
        return
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO gmp_history (catalog_id, gmp_percent, recorded_at) VALUES (?, ?, ?)",
            (catalog_id, gmp_percent, now),
        )
        conn.execute(
            """
            DELETE FROM gmp_history WHERE catalog_id = ? AND id NOT IN (
                SELECT id FROM gmp_history WHERE catalog_id = ?
                ORDER BY recorded_at DESC, id DESC LIMIT ?
            )
            """,
            (catalog_id, catalog_id, _MAX_SAMPLES_PER_CATALOG),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent(catalog_id: str, limit: int = _MAX_SAMPLES_PER_CATALOG) -> list[GmpSample]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT catalog_id, gmp_percent, recorded_at FROM gmp_history "
            "WHERE catalog_id = ? ORDER BY recorded_at DESC, id DESC LIMIT ?",
            (catalog_id, limit),
        ).fetchall()
    finally:
        conn.close()
    return [GmpSample(catalog_id=row["catalog_id"], gmp_percent=row["gmp_percent"], recorded_at=row["recorded_at"]) for row in rows]
