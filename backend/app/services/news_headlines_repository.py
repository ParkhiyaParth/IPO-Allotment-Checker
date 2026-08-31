"""SQLite-backed cache of the individual news headlines behind each IPO's
news_sentiment_cache score (see news_client.py + news_market_refresh_service).
Unlike ipo_catalog's COALESCE-merge upserts, this is a full replace per
catalog_id on every daily refresh -- the headline list itself isn't a set
of sparse fields to preserve piecemeal, it's "today's top ~20 headlines",
which should reflect exactly what the latest fetch returned.
"""

from dataclasses import dataclass

from app.db.database import get_connection
from app.scrapers.news.news_client import NewsHeadline


@dataclass
class CachedHeadline:
    title: str
    link: str | None
    source: str | None
    published_at: str | None


def replace_all(catalog_id: str, headlines: list[NewsHeadline]) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM news_headlines_cache WHERE catalog_id = ?", (catalog_id,))
        conn.executemany(
            """
            INSERT INTO news_headlines_cache (catalog_id, rank, title, link, source, published_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [(catalog_id, i, h.title, h.link, h.source, h.published_at) for i, h in enumerate(headlines)],
        )
        conn.commit()
    finally:
        conn.close()


def get(catalog_id: str) -> list[CachedHeadline]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM news_headlines_cache WHERE catalog_id = ? ORDER BY rank", (catalog_id,)
        ).fetchall()
        return [
            CachedHeadline(title=r["title"], link=r["link"], source=r["source"], published_at=r["published_at"])
            for r in rows
        ]
    finally:
        conn.close()
