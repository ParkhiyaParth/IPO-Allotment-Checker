from app.services import ipo_historical_repository
from app.services.ipo_historical_repository import HistoricalOutcome


def _outcome(**overrides) -> HistoricalOutcome:
    defaults = dict(id="hist-acme", company_name="Acme Ltd")
    defaults.update(overrides)
    return HistoricalOutcome(**defaults)


def test_upsert_and_get_all_roundtrip():
    ipo_historical_repository.upsert_many([_outcome(gmp_percent_at_close=20.0, listing_gain_percent=15.0)])

    all_rows = ipo_historical_repository.get_all()

    assert len(all_rows) == 1
    assert all_rows[0].company_name == "Acme Ltd"
    assert all_rows[0].gmp_percent_at_close == 20.0
    assert all_rows[0].listing_gain_percent == 15.0


def test_upsert_does_not_null_out_previously_known_fields():
    ipo_historical_repository.upsert_many([_outcome(pe_ratio=25.0)])

    # A later merge pass that only has performance-report fields (no P/E,
    # since that only comes from the subscription report) must not wipe
    # the previously-known P/E.
    ipo_historical_repository.upsert_many([_outcome(pe_ratio=None, listing_gain_percent=10.0)])

    result = ipo_historical_repository.get_all()[0]
    assert result.pe_ratio == 25.0
    assert result.listing_gain_percent == 10.0


def test_get_base_rate_matches_similar_gmp_and_size():
    ipo_historical_repository.upsert_many(
        [
            _outcome(id="hist-a", gmp_percent_at_close=20.0, issue_size_cr=100.0, listing_gain_percent=15.0),
            _outcome(id="hist-b", gmp_percent_at_close=22.0, issue_size_cr=120.0, listing_gain_percent=-5.0),
            # Far outside GMP tolerance -- must not be counted.
            _outcome(id="hist-c", gmp_percent_at_close=90.0, issue_size_cr=110.0, listing_gain_percent=50.0),
        ]
    )

    total, positive = ipo_historical_repository.get_base_rate(gmp_percent=21.0, issue_size_cr=110.0)

    assert total == 2
    assert positive == 1


def test_get_base_rate_uses_current_gain_when_listing_gain_unknown():
    ipo_historical_repository.upsert_many(
        [_outcome(gmp_percent_at_close=20.0, issue_size_cr=100.0, listing_gain_percent=None, current_gain_percent=8.0)]
    )

    total, positive = ipo_historical_repository.get_base_rate(gmp_percent=20.0, issue_size_cr=100.0)

    assert total == 1
    assert positive == 1


def test_get_base_rate_skips_outcomes_with_no_known_result():
    ipo_historical_repository.upsert_many(
        [_outcome(gmp_percent_at_close=20.0, issue_size_cr=100.0, listing_gain_percent=None, current_gain_percent=None)]
    )

    total, positive = ipo_historical_repository.get_base_rate(gmp_percent=20.0, issue_size_cr=100.0)

    assert total == 0
    assert positive == 0


def test_get_base_rate_with_no_filters_matches_everything_with_a_known_result():
    ipo_historical_repository.upsert_many(
        [
            _outcome(id="hist-a", listing_gain_percent=15.0),
            _outcome(id="hist-b", listing_gain_percent=-15.0),
        ]
    )

    total, positive = ipo_historical_repository.get_base_rate(gmp_percent=None, issue_size_cr=None)

    assert total == 2
    assert positive == 1


def test_get_similar_outcomes_returns_the_matched_records_not_just_counts():
    ipo_historical_repository.upsert_many(
        [
            _outcome(
                id="hist-a",
                company_name="Alpha Ltd",
                gmp_percent_at_close=20.0,
                issue_size_cr=100.0,
                listing_gain_percent=15.0,
            ),
            # Far outside GMP tolerance -- must not be included.
            _outcome(
                id="hist-b",
                company_name="Beta Ltd",
                gmp_percent_at_close=90.0,
                issue_size_cr=110.0,
                listing_gain_percent=50.0,
            ),
        ]
    )

    result = ipo_historical_repository.get_similar_outcomes(gmp_percent=21.0, issue_size_cr=110.0)

    assert [o.company_name for o in result] == ["Alpha Ltd"]


def test_get_similar_outcomes_sorts_most_recent_first_and_respects_limit():
    ipo_historical_repository.upsert_many(
        [
            _outcome(
                id=f"hist-{i}",
                company_name=f"Company {i}",
                listing_date=f"2026-01-{i:02d}",
                listing_gain_percent=5.0,
            )
            for i in range(1, 8)
        ]
    )

    result = ipo_historical_repository.get_similar_outcomes(gmp_percent=None, issue_size_cr=None, limit=3)

    assert len(result) == 3
    assert [o.listing_date for o in result] == ["2026-01-07", "2026-01-06", "2026-01-05"]
