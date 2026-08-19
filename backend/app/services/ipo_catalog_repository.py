"""SQLite-backed cache of IPO calendar/GMP/subscription/price data sourced
from NSE and Chittorgarh — separate from ipo_cache (the registrar-based
allotment-check cache), linked to it only via linked_registrar_ipo_id.

Upserts use COALESCE so a refresh where one source failed (and so omits
some fields) never nulls out previously-known values for those fields —
only a field the incoming record actually has data for overwrites the
cached one.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from app.db.database import get_connection

_FIELDS = [
    "company_name", "nse_symbol", "chittorgarh_slug", "open_date", "close_date",
    "price_band_low", "price_band_high", "issue_price", "lot_size", "issue_size_cr",
    "gmp_value", "gmp_percent", "gmp_updated_at",
    "sub_qib_offered", "sub_qib_applied", "sub_hni_offered", "sub_hni_applied",
    "sub_retail_offered", "sub_retail_applied", "sub_updated_at",
    "boa_date", "listing_date", "listing_price", "current_price", "current_price_updated_at",
    "linked_registrar_ipo_id", "notified_apply_signal", "signal_accuracy_logged", "gmp_momentum_alerted_at",
    "auto_checked_boa", "rating", "pe_ratio",
]


@dataclass
class CatalogRecord:
    id: str
    company_name: str
    nse_symbol: str | None = None
    chittorgarh_slug: str | None = None
    open_date: str | None = None
    close_date: str | None = None
    price_band_low: float | None = None
    price_band_high: float | None = None
    issue_price: float | None = None
    lot_size: int | None = None
    issue_size_cr: float | None = None
    gmp_value: float | None = None
    gmp_percent: float | None = None
    gmp_updated_at: str | None = None
    sub_qib_offered: int | None = None
    sub_qib_applied: int | None = None
    sub_hni_offered: int | None = None
    sub_hni_applied: int | None = None
    sub_retail_offered: int | None = None
    sub_retail_applied: int | None = None
    sub_updated_at: str | None = None
    boa_date: str | None = None
    listing_date: str | None = None
    listing_price: float | None = None
    current_price: float | None = None
    current_price_updated_at: str | None = None
    linked_registrar_ipo_id: str | None = None
    notified_apply_signal: str = ""
    signal_accuracy_logged: str = ""
    gmp_momentum_alerted_at: str = ""
    auto_checked_boa: str = ""
    rating: int | None = None
    pe_ratio: float | None = None
    first_seen_at: str = ""
    last_seen_at: str = ""


def upsert_many(records: list[CatalogRecord]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        for r in records:
            values = [getattr(r, f) for f in _FIELDS]
            set_clause = ", ".join(f"{f} = COALESCE(excluded.{f}, ipo_catalog.{f})" for f in _FIELDS)
            conn.execute(
                f"""
                INSERT INTO ipo_catalog (id, {", ".join(_FIELDS)}, first_seen_at, last_seen_at)
                VALUES (?, {", ".join("?" for _ in _FIELDS)}, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    {set_clause},
                    last_seen_at = excluded.last_seen_at
                """,
                (r.id, *values, r.first_seen_at or now, now),
            )
        conn.commit()
    finally:
        conn.close()


def get_all() -> list[CatalogRecord]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM ipo_catalog").fetchall()
        return [_row_to_record(row) for row in rows]
    finally:
        conn.close()


def get_by_id(catalog_id: str) -> CatalogRecord | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM ipo_catalog WHERE id = ?", (catalog_id,)).fetchone()
        return _row_to_record(row) if row else None
    finally:
        conn.close()


def get_by_linked_registrar_id(registrar_ipo_id: str) -> CatalogRecord | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM ipo_catalog WHERE linked_registrar_ipo_id = ? LIMIT 1", (registrar_ipo_id,)
        ).fetchone()
        return _row_to_record(row) if row else None
    finally:
        conn.close()


def _row_to_record(row) -> CatalogRecord:
    return CatalogRecord(**{f: row[f] for f in ["id", *_FIELDS, "first_seen_at", "last_seen_at"]})
