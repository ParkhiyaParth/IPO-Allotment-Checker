"""Tracks how often the apply_signal heuristic (ipo_catalog_service.compute_apply_signal)
was actually right, logged once per IPO the first time its status becomes
"closed" with a real current_price -- see ipo_catalog_service.refresh()'s
consolidated per-record pass for when this gets called.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from app.db.database import get_connection


@dataclass
class SignalAccuracyEntry:
    catalog_id: str
    company_name: str
    signal_at_close: str
    was_profitable: bool
    logged_at: str


def insert(entry: SignalAccuracyEntry) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO signal_accuracy_log
                (catalog_id, company_name, signal_at_close, was_profitable, logged_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(catalog_id) DO NOTHING
            """,
            (entry.catalog_id, entry.company_name, entry.signal_at_close, int(entry.was_profitable), entry.logged_at),
        )
        conn.commit()
    finally:
        conn.close()


def get_stats() -> dict:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT signal_at_close, was_profitable FROM signal_accuracy_log").fetchall()
    finally:
        conn.close()

    by_signal: dict[str, dict] = {}
    total = 0
    correct = 0
    for row in rows:
        signal = row["signal_at_close"]
        was_profitable = bool(row["was_profitable"])
        # "Correct" means the signal's own recommendation matched the outcome:
        # strong_apply/consider are a "should profit" call, skip is a "won't"
        # call -- so skip is correct when it wasn't profitable, not when it was.
        is_correct = was_profitable if signal != "skip" else not was_profitable

        bucket = by_signal.setdefault(signal, {"total": 0, "correct": 0})
        bucket["total"] += 1
        bucket["correct"] += int(is_correct)
        total += 1
        correct += int(is_correct)

    return {
        "total": total,
        "correct": correct,
        "hit_rate": (correct / total) if total else None,
        "by_signal": {
            signal: {
                "total": bucket["total"],
                "correct": bucket["correct"],
                "hit_rate": (bucket["correct"] / bucket["total"]) if bucket["total"] else None,
            }
            for signal, bucket in by_signal.items()
        },
    }
