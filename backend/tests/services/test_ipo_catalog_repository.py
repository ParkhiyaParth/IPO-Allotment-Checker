from app.services import ipo_catalog_repository
from app.services.ipo_catalog_repository import CatalogRecord


def _record(**overrides) -> CatalogRecord:
    defaults = dict(
        id="catalog-acme",
        company_name="Acme Ltd",
        nse_symbol="ACME",
        chittorgarh_slug=None,
        open_date="2026-08-14",
        close_date="2026-08-18",
        price_band_low=125.0,
        price_band_high=132.0,
        lot_size=1000,
        issue_size_cr=60.98,
        gmp_value=30.0,
        gmp_percent=23.0,
        gmp_updated_at="2026-08-17T14:34:00+00:00",
        sub_qib_offered=877000,
        sub_qib_applied=782000,
        sub_hni_offered=660000,
        sub_hni_applied=3793000,
        sub_retail_offered=1538000,
        sub_retail_applied=12978000,
        sub_updated_at="2026-08-18T09:59:07+00:00",
        listing_date=None,
        listing_price=None,
        current_price=None,
        current_price_updated_at=None,
        linked_registrar_ipo_id="linkintime-1",
        first_seen_at="2026-08-14T00:00:00+00:00",
        last_seen_at="2026-08-14T00:00:00+00:00",
    )
    defaults.update(overrides)
    return CatalogRecord(**defaults)


def test_upsert_and_get_by_id_roundtrip():
    ipo_catalog_repository.upsert_many([_record()])

    result = ipo_catalog_repository.get_by_id("catalog-acme")

    assert result is not None
    assert result.company_name == "Acme Ltd"
    assert result.gmp_value == 30.0
    assert result.sub_qib_applied == 782000


def test_get_all_returns_every_row():
    ipo_catalog_repository.upsert_many([_record(), _record(id="catalog-beta", company_name="Beta Ltd")])

    assert {r.id for r in ipo_catalog_repository.get_all()} == {"catalog-acme", "catalog-beta"}


def test_get_by_id_returns_none_when_missing():
    assert ipo_catalog_repository.get_by_id("does-not-exist") is None


def test_upsert_does_not_null_out_previously_known_fields():
    ipo_catalog_repository.upsert_many([_record()])

    # A refresh where GMP scraping failed omits gmp_value/gmp_percent —
    # the previously-cached values must survive, not be overwritten with None.
    ipo_catalog_repository.upsert_many([_record(gmp_value=None, gmp_percent=None, gmp_updated_at=None)])

    result = ipo_catalog_repository.get_by_id("catalog-acme")
    assert result.gmp_value == 30.0
    assert result.gmp_percent == 23.0
