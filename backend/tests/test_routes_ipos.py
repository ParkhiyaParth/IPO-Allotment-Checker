from app.api.routes_ipos import _profit_per_lot
from app.services.ipo_catalog_repository import CatalogRecord


def _record(**overrides) -> CatalogRecord:
    defaults = dict(id="catalog-test", company_name="Test Co", first_seen_at="2026-01-01T00:00:00Z")
    defaults.update(overrides)
    return CatalogRecord(**defaults)


def test_profit_per_lot_uses_actual_once_listed():
    record = _record(current_price=250.0, issue_price=200.0, lot_size=50, gmp_value=75.0)

    profit, basis = _profit_per_lot(record)

    # Real profit must win over the GMP estimate once real numbers exist --
    # GMP is a pre-listing guess, not something to keep showing afterwards.
    assert basis == "actual"
    assert profit == (250.0 - 200.0) * 50


def test_profit_per_lot_falls_back_to_gmp_estimate_before_listing():
    record = _record(current_price=None, issue_price=None, lot_size=41, gmp_value=75.0)

    profit, basis = _profit_per_lot(record)

    assert basis == "estimated"
    assert profit == 75.0 * 41


def test_profit_per_lot_none_when_nothing_available():
    record = _record(current_price=None, issue_price=None, lot_size=41, gmp_value=None)

    profit, basis = _profit_per_lot(record)

    assert profit is None
    assert basis is None


def test_profit_per_lot_none_without_lot_size():
    # A lot size of 0/None makes the multiplication meaningless -- must not
    # silently return 0, which would misleadingly read as "no profit".
    record = _record(current_price=250.0, issue_price=200.0, lot_size=None, gmp_value=75.0)

    profit, basis = _profit_per_lot(record)

    assert profit is None
    assert basis is None
