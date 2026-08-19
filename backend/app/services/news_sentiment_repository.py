"""SQLite-backed cache of per-IPO news sentiment (see sentiment.py +
news_client.py), refreshed at most daily -- news doesn't move fast enough
to justify the 5-min catalog refresh cadence, so this is a single latest
row per catalog_id, not a history table.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from app.db.database import get_connection


@dataclass
class NewsSentiment:
    catalog_id: str
    sentiment_score: float | None
    headline_count: int
    computed_at: str


def upsert(catalog_id: str, sentiment_score: float | None, headline_count: int) -> None:
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO news_sentiment_cache (catalog_id, sentiment_score, headline_count, computed_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(catalog_id) DO UPDATE SET
                sentiment_score = excluded.sentiment_score,
                headline_count = excluded.headline_count,
                computed_at = excluded.computed_at
            """,
            (catalog_id, sentiment_score, headline_count, now),
        )
        conn.commit()
    finally:
        conn.close()


def get(catalog_id: str) -> NewsSentiment | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM news_sentiment_cache WHERE catalog_id = ?", (catalog_id,)
        ).fetchone()
        return _row_to_sentiment(row) if row else None
    finally:
        conn.close()


def _row_to_sentiment(row) -> NewsSentiment:
    return NewsSentiment(
        catalog_id=row["catalog_id"],
        sentiment_score=row["sentiment_score"],
        headline_count=row["headline_count"],
        computed_at=row["computed_at"],
    )
