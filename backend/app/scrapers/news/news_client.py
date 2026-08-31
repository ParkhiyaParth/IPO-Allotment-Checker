"""Client for Google News' free, no-API-key RSS search feed -- confirmed
live (2026-08-19): plain RSS 2.0 XML, no JS, no auth, at
`news.google.com/rss/search?q=...`. Each <item>'s <title> has the source
publication appended after " - " (e.g. "... - Moneycontrol.com"), stripped
off here since it's not part of the actual headline text sentiment.py
scores.
"""

from dataclasses import dataclass
from xml.etree import ElementTree

from app.utils.http_client import get_http_client

RSS_URL = "https://news.google.com/rss/search"
# The feed itself has no pagination and caps out around 100 items; capped
# far below that here since only the last day or two of headlines are
# relevant to an "is this IPO getting good press right now" signal.
_MAX_HEADLINES = 20


@dataclass
class NewsHeadline:
    title: str
    published_at: str | None  # RFC 2822 string as sent by the feed, unparsed
    source: str | None
    link: str | None = None


def _strip_source_suffix(title: str, source: str | None) -> str:
    if source and title.endswith(f" - {source}"):
        return title[: -(len(source) + 3)]
    return title


async def get_headlines(query: str, limit: int = _MAX_HEADLINES) -> list[NewsHeadline]:
    client = get_http_client()
    resp = await client.get(RSS_URL, params={"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"})
    resp.raise_for_status()

    root = ElementTree.fromstring(resp.text)
    headlines: list[NewsHeadline] = []
    for item in root.findall("./channel/item")[:limit]:
        title_el = item.find("title")
        if title_el is None or not title_el.text:
            continue
        source_el = item.find("source")
        source = source_el.text if source_el is not None else None
        pub_date_el = item.find("pubDate")
        link_el = item.find("link")
        headlines.append(
            NewsHeadline(
                title=_strip_source_suffix(title_el.text, source),
                published_at=pub_date_el.text if pub_date_el is not None else None,
                source=source,
                link=link_el.text if link_el is not None else None,
            )
        )
    return headlines
