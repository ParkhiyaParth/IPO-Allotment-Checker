from app.services.ipo_catalog_repository import CatalogRecord
from app.services.ipo_catalog_service import compute_apply_signal


def _record(**overrides) -> CatalogRecord:
    defaults = dict(id="catalog-test", company_name="Test Co", first_seen_at="2026-01-01T00:00:00Z")
    defaults.update(overrides)
    return CatalogRecord(**defaults)


def test_apply_signal_none_when_no_data_at_all():
    record = _record()

    signal, reason = compute_apply_signal(record)

    assert signal is None
    assert reason is None


def test_apply_signal_strong_apply_on_high_gmp_and_heavy_qib_demand():
    record = _record(gmp_percent=25.0, sub_qib_offered=100, sub_qib_applied=1500)

    signal, reason = compute_apply_signal(record)

    assert signal == "strong_apply"
    assert "GMP +25%" in reason
    assert "QIB 15.0x" in reason


def test_apply_signal_skip_on_negative_gmp():
    record = _record(gmp_percent=-10.0)

    signal, reason = compute_apply_signal(record)

    assert signal == "skip"
    assert "GMP -10%" in reason


def test_apply_signal_consider_on_moderate_gmp_alone():
    record = _record(gmp_percent=8.0)

    signal, reason = compute_apply_signal(record)

    assert signal == "consider"


def test_apply_signal_uses_only_gmp_when_subscription_unavailable():
    # An upcoming IPO with GMP already trading but bidding not yet open --
    # subscription data can't exist yet, so the signal must still resolve
    # from GMP alone rather than returning None just because one input
    # is missing. A single signal caps out at "consider" -- "strong_apply"
    # deliberately requires more than one confirming data point.
    record = _record(gmp_percent=22.0, sub_qib_offered=None, sub_qib_applied=None)

    signal, reason = compute_apply_signal(record)

    assert signal == "consider"
    assert reason == "GMP +22%"
