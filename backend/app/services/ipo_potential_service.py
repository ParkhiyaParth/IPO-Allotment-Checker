"""v1 "IPO Potential Score" -- a fully transparent, multi-factor score
enriching the existing GMP+subscription apply_signal (ipo_catalog_service.
compute_apply_signal) with news sentiment, broad-market momentum, and
REAL historical base-rate statistics from past IPOs
(ipo_historical_repository.get_base_rate).

This is deliberately NOT a trained ML model. The app's own outcome log
(signal_accuracy_log) has only been collecting real results for a few
days -- training anything on that little data would confidently overfit
noise, not predict accurately. A real model (scikit-learn, trained
offline, gated behind an explicit sample-count threshold once enough
history exists) is planned as a separate, later phase. Until then, every
score here is a sum of explainable, individually-labeled factors --
every result carries its own `reasons`, never a bare number.

`has_anchor` (from investorgain's live report) is deliberately NOT scored
here: in the one live sample checked during this feature's Phase 0 spike,
every single current IPO had it set True, so it isn't currently observed
to discriminate between outcomes -- scoring on it would be noise dressed
up as signal. It's still parsed and available for whenever it's confirmed
to vary.
"""

from dataclasses import dataclass, field

from app.services import ipo_historical_repository, market_trend_repository, news_sentiment_repository
from app.services.ipo_catalog_repository import CatalogRecord

_MIN_BASE_RATE_SAMPLE = 3

_STRONG_POTENTIAL_SCORE = 6
_PROMISING_SCORE = 2
_WEAK_SCORE = -3

_BROAD_MARKET_INDEX = "NIFTY 50"


@dataclass
class PotentialResult:
    label: str | None = None  # "strong_potential" | "promising" | "uncertain" | "weak"
    score: int | None = None  # 0-100, an approximate display-only normalization -- not a probability
    reasons: list[str] = field(default_factory=list)
    basis: str | None = None  # "historical_stats" (only basis v1 ever produces)


def _score_to_display(raw_score: int) -> int:
    """Linear rescale of the raw point total (roughly -8..10 in practice)
    into a friendlier 0-100 range for display. This is NOT a calibrated
    probability -- just a readable stand-in for the raw point total."""
    clamped = max(-8, min(10, raw_score))
    return round((clamped + 8) / 18 * 100)


def compute_potential_score(record: CatalogRecord) -> PotentialResult:
    raw_score = 0
    reasons: list[str] = []
    have_signal = False

    total, positive = ipo_historical_repository.get_base_rate(record.gmp_percent, record.issue_size_cr)
    if total >= _MIN_BASE_RATE_SAMPLE:
        have_signal = True
        rate = positive / total
        if rate >= 0.7:
            raw_score += 3
        elif rate >= 0.5:
            raw_score += 1
        elif rate < 0.3:
            raw_score -= 3
        else:
            raw_score -= 1
        reasons.append(f"{total} similar past IPOs listed positively {rate * 100:.0f}% of the time")

    if record.rating is not None:
        have_signal = True
        if record.rating >= 4:
            raw_score += 2
        elif record.rating == 3:
            raw_score += 1
        elif record.rating <= 1:
            raw_score -= 1
        reasons.append(f"Investorgain rating {record.rating}/5")

    if record.pe_ratio is not None:
        have_signal = True
        if record.pe_ratio < 0:
            raw_score -= 1
            reasons.append("Loss-making (negative P/E)")
        elif record.pe_ratio > 60:
            raw_score -= 1
            reasons.append(f"P/E {record.pe_ratio:.1f} (richly valued)")
        elif record.pe_ratio <= 25:
            raw_score += 1
            reasons.append(f"P/E {record.pe_ratio:.1f} (reasonably valued)")

    sentiment = news_sentiment_repository.get(record.id)
    if sentiment is not None and sentiment.sentiment_score is not None and sentiment.headline_count > 0:
        have_signal = True
        score = sentiment.sentiment_score
        if score >= 0.3:
            raw_score += 2
            reasons.append(f"Positive news coverage ({sentiment.headline_count} headlines)")
        elif score >= 0.1:
            raw_score += 1
            reasons.append(f"Mildly positive news coverage ({sentiment.headline_count} headlines)")
        elif score <= -0.2:
            raw_score -= 2
            reasons.append(f"Negative news coverage ({sentiment.headline_count} headlines)")

    market = market_trend_repository.get(_BROAD_MARKET_INDEX)
    if market is not None and market.percent_change_30d is not None:
        have_signal = True
        if market.percent_change_30d >= 3:
            raw_score += 1
            reasons.append(f"Broader market up {market.percent_change_30d:.1f}% over 30 days")
        elif market.percent_change_30d <= -3:
            raw_score -= 1
            reasons.append(f"Broader market down {abs(market.percent_change_30d):.1f}% over 30 days")

    if not have_signal:
        return PotentialResult()

    if raw_score >= _STRONG_POTENTIAL_SCORE:
        label = "strong_potential"
    elif raw_score >= _PROMISING_SCORE:
        label = "promising"
    elif raw_score <= _WEAK_SCORE:
        label = "weak"
    else:
        label = "uncertain"

    return PotentialResult(label=label, score=_score_to_display(raw_score), reasons=reasons, basis="historical_stats")
