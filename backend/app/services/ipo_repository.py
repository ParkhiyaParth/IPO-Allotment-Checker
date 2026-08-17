"""SQLite-backed cache of non-PII IPO metadata.

There's no registrar API that reports an IPO's actual allotment-finalization
date, so `first_seen_at` (when our own scheduled refresh first noticed this
IPO in a registrar's "available to check" list) is used as the recency
signal instead. It's a proxy, not an authoritative published date: it lags
behind the registrar's real finalization by however long it took our next
refresh cycle to notice. Documented here rather than overclaiming precision
in the API response.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from app.db.database import get_connection


@dataclass
class CachedIpo:
    id: str
    company_name: str
    registrar: str
    registrar_ipo_identifier: str
    automation_supported: bool
    first_seen_at: str
    list_rank: int = 0


def upsert_many(records: list[CachedIpo]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        for r in records:
            conn.execute(
                """
                INSERT INTO ipo_cache (id, company_name, registrar, registrar_ipo_identifier,
                                        automation_supported, first_seen_at, last_seen_at, list_rank)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    company_name = excluded.company_name,
                    automation_supported = excluded.automation_supported,
                    last_seen_at = excluded.last_seen_at,
                    list_rank = excluded.list_rank
                """,
                (r.id, r.company_name, r.registrar, r.registrar_ipo_identifier,
                 int(r.automation_supported), r.first_seen_at, now, r.list_rank),
            )
        conn.commit()
    finally:
        conn.close()


def get_recent(limit: int = 15) -> list[CachedIpo]:
    conn = get_connection()
    try:
        # list_rank is each registrar's own list order (their best signal for
        # recency, since none of them publish an actual allotment date) —
        # first_seen_at as primary key would just reflect our own refresh
        # timing, not the registrar's ordering, so rank first within a
        # registrar and only fall back to first_seen_at across registrars.
        rows = conn.execute(
            "SELECT * FROM ipo_cache ORDER BY first_seen_at DESC, list_rank ASC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_record(row) for row in rows]
    finally:
        conn.close()


def get_by_id(ipo_id: str) -> CachedIpo | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM ipo_cache WHERE id = ?", (ipo_id,)).fetchone()
        return _row_to_record(row) if row else None
    finally:
        conn.close()


def is_empty() -> bool:
    conn = get_connection()
    try:
        return conn.execute("SELECT 1 FROM ipo_cache LIMIT 1").fetchone() is None
    finally:
        conn.close()


def get_ids_for_registrar(registrar: str) -> set[str]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id FROM ipo_cache WHERE registrar = ?", (registrar,)).fetchall()
        return {row["id"] for row in rows}
    finally:
        conn.close()


def prune_registrar(registrar: str, keep_ids: list[str]) -> None:
    """Removes cached rows for a registrar that are no longer in its current
    list — e.g. entries that get filtered out (NCDs/InvITs) after this cache
    already stored them from an earlier refresh, or IPOs the registrar has
    since dropped from its own dropdown. Only touches rows for the given
    registrar, so a failed refresh for a different registrar never loses
    that registrar's existing cached data.
    """
    conn = get_connection()
    try:
        if keep_ids:
            placeholders = ",".join("?" * len(keep_ids))
            conn.execute(
                f"DELETE FROM ipo_cache WHERE registrar = ? AND id NOT IN ({placeholders})",
                (registrar, *keep_ids),
            )
        else:
            conn.execute("DELETE FROM ipo_cache WHERE registrar = ?", (registrar,))
        conn.commit()
    finally:
        conn.close()


def _row_to_record(row) -> CachedIpo:
    return CachedIpo(
        id=row["id"],
        company_name=row["company_name"],
        registrar=row["registrar"],
        registrar_ipo_identifier=row["registrar_ipo_identifier"],
        automation_supported=bool(row["automation_supported"]),
        first_seen_at=row["first_seen_at"],
        list_rank=row["list_rank"],
    )
