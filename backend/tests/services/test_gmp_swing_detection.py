from datetime import datetime, timedelta, timezone

from app.services import gmp_history_repository
from app.services.ipo_catalog_service import _detect_gmp_swing


def _seed_sample(catalog_id: str, gmp_percent: float, hours_ago: float) -> None:
    """gmp_history_repository.append always timestamps "now" -- to test
    swing detection against samples from hours ago, insert directly via the
    same connection helper the repository uses."""
    from app.db.database import get_connection

    conn = get_connection()
    try:
        recorded_at = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
        conn.execute(
            "INSERT INTO gmp_history (catalog_id, gmp_percent, recorded_at) VALUES (?, ?, ?)",
            (catalog_id, gmp_percent, recorded_at),
        )
        conn.commit()
    finally:
        conn.close()


def test_no_swing_when_no_history():
    assert _detect_gmp_swing("catalog-acme", 20.0) is None


def test_swing_detected_when_jump_exceeds_threshold_within_window():
    _seed_sample("catalog-acme", 10.0, hours_ago=2)

    swing = _detect_gmp_swing("catalog-acme", 20.0)

    assert swing == 10.0


def test_no_swing_when_change_is_below_threshold():
    _seed_sample("catalog-acme", 18.0, hours_ago=2)

    assert _detect_gmp_swing("catalog-acme", 20.0) is None


def test_no_swing_when_oldest_sample_is_outside_the_window():
    # 10 hours ago is outside the 6h swing window -- must not compare
    # against a sample too old to represent recent momentum.
    _seed_sample("catalog-acme", 5.0, hours_ago=10)

    assert _detect_gmp_swing("catalog-acme", 25.0) is None


def test_negative_swing_detected_on_a_drop():
    _seed_sample("catalog-acme", 30.0, hours_ago=1)

    swing = _detect_gmp_swing("catalog-acme", 20.0)

    assert swing == -10.0
