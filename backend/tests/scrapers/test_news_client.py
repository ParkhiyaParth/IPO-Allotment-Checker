from pathlib import Path

from app.scrapers.news import news_client
from tests.conftest import FakeAsyncClient, FakeResponse

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


async def test_get_headlines_parses_real_fixture(monkeypatch):
    fixture_xml = (FIXTURES / "google_news_rss.xml").read_text(encoding="utf-8")
    fake_client = FakeAsyncClient({news_client.RSS_URL: FakeResponse(text_data=fixture_xml)})
    monkeypatch.setattr(news_client, "get_http_client", lambda: fake_client)

    headlines = await news_client.get_headlines("Sunshine Pictures IPO")

    assert len(headlines) == 3
    first = headlines[0]
    # Real fixture's raw <title> ends with " - India Infoline" -- the
    # source-publication suffix must be stripped from the headline text
    # itself (sentiment.py should score the actual headline, not a
    # trailing publication name).
    assert first.title == "Sunshine Pictures IPO GMP Today: GMP indicates 21% premium listing"
    assert first.source == "India Infoline"
    assert first.published_at == "Wed, 19 Aug 2026 06:17:20 GMT"
    assert first.link is not None and first.link.startswith("https://news.google.com/rss/articles/")


async def test_get_headlines_respects_limit(monkeypatch):
    fixture_xml = (FIXTURES / "google_news_rss.xml").read_text(encoding="utf-8")
    fake_client = FakeAsyncClient({news_client.RSS_URL: FakeResponse(text_data=fixture_xml)})
    monkeypatch.setattr(news_client, "get_http_client", lambda: fake_client)

    headlines = await news_client.get_headlines("Sunshine Pictures IPO", limit=1)

    assert len(headlines) == 1
