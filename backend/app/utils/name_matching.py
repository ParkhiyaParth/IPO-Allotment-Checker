import re

_SUFFIX_WORDS = {"LIMITED", "LTD", "PRIVATE", "PVT", "IPO"}
_PUNCTUATION = re.compile(r"[^\w\s]")
_WHITESPACE = re.compile(r"\s+")


def normalize_company_name(name: str) -> str:
    """Normalizes a company name for exact-match identity matching across
    NSE, Chittorgarh, and registrar records — not a fuzzy match, so it only
    strips the handful of suffix words/punctuation that vary between
    sources for the same company, never approximates similarity."""
    upper = _PUNCTUATION.sub(" ", name.upper())
    words = [w for w in upper.split() if w not in _SUFFIX_WORDS]
    return _WHITESPACE.sub(" ", " ".join(words)).strip()
