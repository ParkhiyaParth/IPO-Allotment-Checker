from app.services import ipo_historical_repository, market_trend_repository, news_sentiment_repository
from app.services.ipo_catalog_repository import CatalogRecord
from app.services.ipo_historical_repository import HistoricalOutcome
from app.services.ipo_potential_service import compute_potential_score


def _record(**overrides) -> CatalogRecord:
    defaults = dict(id="catalog-test", company_name="Test Co", first_seen_at="2026-01-01T00:00:00Z")
    defaults.update(overrides)
    return CatalogRecord(**defaults)


def test_no_signal_at_all_returns_empty_result():
    result = compute_potential_score(_record())

    assert result.label is None
    assert result.score is None
    assert result.reasons == []
    assert result.basis is None


def test_strong_historical_base_rate_alone_yields_promising_or_better():
    ipo_historical_repository.upsert_many(
        [
            HistoricalOutcome(id="h1", company_name="A", gmp_percent_at_close=20.0, issue_size_cr=100.0, listing_gain_percent=15.0),
            HistoricalOutcome(id="h2", company_name="B", gmp_percent_at_close=21.0, issue_size_cr=110.0, listing_gain_percent=10.0),
            HistoricalOutcome(id="h3", company_name="C", gmp_percent_at_close=22.0, issue_size_cr=90.0, listing_gain_percent=5.0),
        ]
    )
    record = _record(gmp_percent=20.0, issue_size_cr=100.0)

    result = compute_potential_score(record)

    assert result.basis == "historical_stats"
    assert "3 similar past IPOs listed positively 100% of the time" in result.reasons
    assert result.label in ("promising", "strong_potential")


def test_weak_historical_base_rate_pulls_score_down():
    ipo_historical_repository.upsert_many(
        [
            HistoricalOutcome(id="h1", company_name="A", gmp_percent_at_close=20.0, issue_size_cr=100.0, listing_gain_percent=-10.0),
            HistoricalOutcome(id="h2", company_name="B", gmp_percent_at_close=21.0, issue_size_cr=110.0, listing_gain_percent=-5.0),
            HistoricalOutcome(id="h3", company_name="C", gmp_percent_at_close=22.0, issue_size_cr=90.0, listing_gain_percent=-2.0),
        ]
    )
    record = _record(gmp_percent=20.0, issue_size_cr=100.0)

    result = compute_potential_score(record)

    assert result.label == "weak"


def test_high_rating_contributes_positively():
    record = _record(rating=5)

    result = compute_potential_score(record)

    assert "Investorgain rating 5/5" in result.reasons
    assert result.label in ("promising", "strong_potential")


def test_low_rating_contributes_negatively():
    record = _record(rating=1)

    result = compute_potential_score(record)

    assert "Investorgain rating 1/5" in result.reasons
    assert result.label in ("uncertain", "weak")


def test_negative_pe_ratio_flags_loss_making():
    record = _record(pe_ratio=-15.0)

    result = compute_potential_score(record)

    assert "Loss-making (negative P/E)" in result.reasons


def test_very_high_pe_ratio_flags_rich_valuation():
    record = _record(pe_ratio=80.0)

    result = compute_potential_score(record)

    assert any("richly valued" in r for r in result.reasons)


def test_reasonable_pe_ratio_contributes_positively():
    record = _record(pe_ratio=18.0)

    result = compute_potential_score(record)

    assert any("reasonably valued" in r for r in result.reasons)


def test_positive_news_sentiment_contributes_positively():
    news_sentiment_repository.upsert("catalog-test", sentiment_score=0.5, headline_count=10)
    record = _record()

    result = compute_potential_score(record)

    assert any("Positive news coverage" in r for r in result.reasons)


def test_negative_news_sentiment_contributes_negatively():
    news_sentiment_repository.upsert("catalog-test", sentiment_score=-0.4, headline_count=6)
    record = _record()

    result = compute_potential_score(record)

    assert any("Negative news coverage" in r for r in result.reasons)


def test_news_with_zero_headlines_is_ignored_even_if_score_present():
    # Defensive: a cached row with headline_count 0 shouldn't happen in
    # practice (sentiment.score_headlines returns None for an empty list),
    # but must not be treated as a real signal if it ever does.
    news_sentiment_repository.upsert("catalog-test", sentiment_score=0.5, headline_count=0)
    record = _record()

    result = compute_potential_score(record)

    assert result.label is None


def test_positive_broad_market_trend_contributes_positively():
    market_trend_repository.upsert("NIFTY 50", percent_change_1d=0.1, percent_change_30d=5.0)
    record = _record()

    result = compute_potential_score(record)

    assert any("Broader market up" in r for r in result.reasons)


def test_negative_broad_market_trend_contributes_negatively():
    market_trend_repository.upsert("NIFTY 50", percent_change_1d=-0.1, percent_change_30d=-5.0)
    record = _record()

    result = compute_potential_score(record)

    assert any("Broader market down" in r for r in result.reasons)


def test_combining_all_positive_factors_reaches_strong_potential():
    ipo_historical_repository.upsert_many(
        [
            HistoricalOutcome(id="h1", company_name="A", gmp_percent_at_close=20.0, issue_size_cr=100.0, listing_gain_percent=15.0),
            HistoricalOutcome(id="h2", company_name="B", gmp_percent_at_close=21.0, issue_size_cr=110.0, listing_gain_percent=10.0),
            HistoricalOutcome(id="h3", company_name="C", gmp_percent_at_close=22.0, issue_size_cr=90.0, listing_gain_percent=5.0),
        ]
    )
    news_sentiment_repository.upsert("catalog-test", sentiment_score=0.5, headline_count=10)
    market_trend_repository.upsert("NIFTY 50", percent_change_1d=0.1, percent_change_30d=5.0)
    record = _record(gmp_percent=20.0, issue_size_cr=100.0, rating=5, pe_ratio=18.0)

    result = compute_potential_score(record)

    assert result.label == "strong_potential"
    assert result.score is not None
    assert 0 <= result.score <= 100
    assert len(result.reasons) >= 4


def test_score_display_is_clamped_to_0_100_range():
    # Every individual factor at its most negative simultaneously --
    # display score must still clamp into [0, 100], not go negative.
    ipo_historical_repository.upsert_many(
        [
            HistoricalOutcome(id="h1", company_name="A", gmp_percent_at_close=20.0, issue_size_cr=100.0, listing_gain_percent=-10.0),
            HistoricalOutcome(id="h2", company_name="B", gmp_percent_at_close=21.0, issue_size_cr=110.0, listing_gain_percent=-5.0),
            HistoricalOutcome(id="h3", company_name="C", gmp_percent_at_close=22.0, issue_size_cr=90.0, listing_gain_percent=-2.0),
        ]
    )
    news_sentiment_repository.upsert("catalog-test", sentiment_score=-0.5, headline_count=10)
    market_trend_repository.upsert("NIFTY 50", percent_change_1d=-0.1, percent_change_30d=-5.0)
    record = _record(gmp_percent=20.0, issue_size_cr=100.0, rating=1, pe_ratio=-10.0)

    result = compute_potential_score(record)

    assert result.score is not None
    assert 0 <= result.score <= 100
