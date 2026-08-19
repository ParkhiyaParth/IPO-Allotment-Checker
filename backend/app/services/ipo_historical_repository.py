"""SQLite-backed store of real past-IPO outcomes, backfilled from
investorgain's historical performance/subscription reports (see
investorgain_history_client.py) via ipo_historical_backfill_service.py.
This is the "historic data" that grounds compute_historical_base_rate --
genuine statistics from real outcomes, not a trained model (see
ipo_potential_service.py's module docstring for why).
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from app.db.database import get_connection

_FIELDS = [
    "company_name", "listing_date", "issue_size_cr", "issue_price", "pe_ratio",
    "sub_qib_times", "sub_hni_times", "sub_retail_times", "sub_total_times",
    "gmp_percent_at_close", "listing_gain_percent", "current_gain_percent",
]


@dataclass
class HistoricalOutcome:
    id: str
    company_name: str
    listing_date: str | None = None
    issue_size_cr: float | None = None
    issue_price: float | None = None
    pe_ratio: float | None = None
    sub_qib_times: float | None = None
    sub_hni_times: float | None = None
    sub_retail_times: float | None = None
    sub_total_times: float | None = None
    gmp_percent_at_close: float | None = None
    listing_gain_percent: float | None = None
    current_gain_percent: float | None = None
    updated_at: str = ""


def upsert_many(outcomes: list[HistoricalOutcome]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        for o in outcomes:
            values = [getattr(o, f) for f in _FIELDS]
            set_clause = ", ".join(f"{f} = COALESCE(excluded.{f}, ipo_historical_outcomes.{f})" for f in _FIELDS)
            conn.execute(
                f"""
                INSERT INTO ipo_historical_outcomes (id, {", ".join(_FIELDS)}, updated_at)
                VALUES (?, {", ".join("?" for _ in _FIELDS)}, ?)
                ON CONFLICT(id) DO UPDATE SET {set_clause}, updated_at = excluded.updated_at
                """,
                (o.id, *values, now),
            )
        conn.commit()
    finally:
        conn.close()


def get_all() -> list[HistoricalOutcome]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM ipo_historical_outcomes").fetchall()
        return [_row_to_outcome(row) for row in rows]
    finally:
        conn.close()


def get_base_rate(
    gmp_percent: float | None,
    issue_size_cr: float | None,
    gmp_tolerance: float = 10.0,
    size_ratio_tolerance: float = 2.0,
) -> tuple[int, int]:
    """Returns (sample_count, positive_count) for past IPOs whose
    GMP-at-close and issue size were "similar" to the given values --
    within +/-gmp_tolerance percentage points, and within a
    size_ratio_tolerance multiple either way. Either filter is skipped
    (matches everything) when the corresponding input is None, so a record
    still gets a (weaker) base rate even with partial data."""
    outcomes = get_all()
    matches = []
    for o in outcomes:
        if o.listing_gain_percent is None and o.current_gain_percent is None:
            continue  # outcome unknown -- can't count it either way
        if gmp_percent is not None and o.gmp_percent_at_close is not None:
            if abs(o.gmp_percent_at_close - gmp_percent) > gmp_tolerance:
                continue
        if issue_size_cr is not None and o.issue_size_cr is not None and o.issue_size_cr > 0:
            ratio = issue_size_cr / o.issue_size_cr
            if ratio > size_ratio_tolerance or ratio < 1 / size_ratio_tolerance:
                continue
        matches.append(o)

    positive = sum(
        1
        for o in matches
        if (o.listing_gain_percent if o.listing_gain_percent is not None else o.current_gain_percent) > 0
    )
    return len(matches), positive


def _row_to_outcome(row) -> HistoricalOutcome:
    return HistoricalOutcome(**{f: row[f] for f in ["id", *_FIELDS, "updated_at"]})
