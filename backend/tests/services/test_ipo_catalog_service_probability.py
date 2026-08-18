from app.services.ipo_catalog_repository import CatalogRecord
from app.services.ipo_catalog_service import compute_retail_allotment_probability


def _record(**overrides) -> CatalogRecord:
    defaults = dict(id="catalog-test", company_name="Test Co", first_seen_at="2026-01-01T00:00:00Z")
    defaults.update(overrides)
    return CatalogRecord(**defaults)


def test_probability_from_retail_subscription():
    record = _record(sub_retail_offered=1000, sub_retail_applied=4000)

    probability = compute_retail_allotment_probability(record)

    assert probability == 0.25


def test_probability_capped_at_one_when_undersubscribed():
    # Fewer applicants than lots offered -- everyone gets in, not >100%.
    record = _record(sub_retail_offered=1000, sub_retail_applied=400)

    assert compute_retail_allotment_probability(record) == 1.0


def test_probability_none_without_subscription_data():
    record = _record(sub_retail_offered=None, sub_retail_applied=None)

    assert compute_retail_allotment_probability(record) is None


def test_probability_none_when_applied_is_zero():
    record = _record(sub_retail_offered=1000, sub_retail_applied=0)

    assert compute_retail_allotment_probability(record) is None
