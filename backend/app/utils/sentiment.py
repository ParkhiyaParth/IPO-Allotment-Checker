"""Lightweight lexicon-based headline sentiment -- vaderSentiment, not a
transformer/deep model, deliberately: its whole footprint is one small
lexicon file loaded once, appropriate for the 1 OCPU/1GB production box
this runs on (see ipo_potential_service.py's module docstring for why a
real trained model isn't used yet either)."""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()


def score_headline(text: str) -> float:
    """VADER's "compound" score, already normalized to [-1, 1]."""
    return _analyzer.polarity_scores(text)["compound"]


def score_headlines(headlines: list[str]) -> float | None:
    """Mean compound score across headlines. None when there's nothing to
    score, so callers can distinguish "no news found" from "neutral news"."""
    if not headlines:
        return None
    scores = [score_headline(h) for h in headlines]
    return sum(scores) / len(scores)
