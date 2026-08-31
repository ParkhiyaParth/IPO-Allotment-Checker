from app.scrapers.news.news_client import NewsHeadline
from app.services import news_headlines_repository


def test_replace_all_and_get_roundtrip():
    news_headlines_repository.replace_all(
        "catalog-acme",
        [
            NewsHeadline(title="First headline", published_at="Wed, 19 Aug 2026 06:17:20 GMT", source="Moneycontrol", link="https://example.com/1"),
            NewsHeadline(title="Second headline", published_at=None, source=None, link=None),
        ],
    )

    result = news_headlines_repository.get("catalog-acme")

    assert [h.title for h in result] == ["First headline", "Second headline"]
    assert result[0].link == "https://example.com/1"
    assert result[0].source == "Moneycontrol"


def test_get_returns_empty_list_when_missing():
    assert news_headlines_repository.get("catalog-does-not-exist") == []


def test_replace_all_replaces_the_previous_set_wholesale():
    news_headlines_repository.replace_all(
        "catalog-acme", [NewsHeadline(title="Old headline", published_at=None, source=None, link=None)]
    )

    news_headlines_repository.replace_all(
        "catalog-acme", [NewsHeadline(title="New headline", published_at=None, source=None, link=None)]
    )

    result = news_headlines_repository.get("catalog-acme")
    assert [h.title for h in result] == ["New headline"]


def test_replace_all_with_empty_list_clears_cached_headlines():
    news_headlines_repository.replace_all(
        "catalog-acme", [NewsHeadline(title="Old headline", published_at=None, source=None, link=None)]
    )

    news_headlines_repository.replace_all("catalog-acme", [])

    assert news_headlines_repository.get("catalog-acme") == []
