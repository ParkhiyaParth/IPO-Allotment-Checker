from app.services import market_trend_repository


def test_upsert_and_get_roundtrip():
    market_trend_repository.upsert("NIFTY 50", percent_change_1d=-0.42, percent_change_30d=-1.16)

    result = market_trend_repository.get("NIFTY 50")

    assert result is not None
    assert result.percent_change_1d == -0.42
    assert result.percent_change_30d == -1.16


def test_get_returns_none_when_missing():
    assert market_trend_repository.get("NIFTY 50") is None


def test_upsert_overwrites_previous_value():
    market_trend_repository.upsert("NIFTY 50", percent_change_1d=-0.42, percent_change_30d=-1.16)
    market_trend_repository.upsert("NIFTY 50", percent_change_1d=1.0, percent_change_30d=2.0)

    result = market_trend_repository.get("NIFTY 50")

    assert result.percent_change_1d == 1.0
    assert result.percent_change_30d == 2.0


def test_different_indices_are_independent():
    market_trend_repository.upsert("NIFTY 50", percent_change_1d=-0.42, percent_change_30d=-1.16)
    market_trend_repository.upsert("NIFTY AUTO", percent_change_1d=5.0, percent_change_30d=7.57)

    assert market_trend_repository.get("NIFTY 50").percent_change_1d == -0.42
    assert market_trend_repository.get("NIFTY AUTO").percent_change_1d == 5.0
