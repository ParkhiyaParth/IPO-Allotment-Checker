from app.services import news_sentiment_repository


def test_upsert_and_get_roundtrip():
    news_sentiment_repository.upsert("catalog-acme", sentiment_score=0.35, headline_count=8)

    result = news_sentiment_repository.get("catalog-acme")

    assert result is not None
    assert result.sentiment_score == 0.35
    assert result.headline_count == 8


def test_get_returns_none_when_missing():
    assert news_sentiment_repository.get("catalog-does-not-exist") is None


def test_upsert_overwrites_previous_value():
    news_sentiment_repository.upsert("catalog-acme", sentiment_score=0.35, headline_count=8)
    news_sentiment_repository.upsert("catalog-acme", sentiment_score=-0.1, headline_count=3)

    result = news_sentiment_repository.get("catalog-acme")

    assert result.sentiment_score == -0.1
    assert result.headline_count == 3


def test_upsert_allows_none_sentiment_when_no_headlines_found():
    news_sentiment_repository.upsert("catalog-acme", sentiment_score=None, headline_count=0)

    result = news_sentiment_repository.get("catalog-acme")

    assert result.sentiment_score is None
    assert result.headline_count == 0
