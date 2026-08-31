from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import AllotmentStatus

PAN_PATTERN = r"^[A-Z]{5}[0-9]{4}[A-Z]$"


class IPOSummary(BaseModel):
    id: str
    company_name: str
    registrar: str
    allotment_date: date
    listing_date: date | None = None
    automation_supported: bool = True


class RecentIposResponse(BaseModel):
    ipos: list[IPOSummary]
    generated_at: datetime


class Applicant(BaseModel):
    pan: str = Field(pattern=PAN_PATTERN)
    label: str


class CheckAllotmentRequest(BaseModel):
    applicants: list[Applicant]


class AllotmentResultItem(BaseModel):
    pan: str
    label: str
    status: AllotmentStatus
    shares_allotted: int | None = None
    manual_check_url: str | None = None
    message: str | None = None


class CheckAllotmentResponse(BaseModel):
    ipo_id: str
    results: list[AllotmentResultItem]
    checked_at: datetime


class RegisterPushTokenRequest(BaseModel):
    token: str = Field(pattern=r"^ExponentPushToken\[.+\]$")
    device_id: str | None = None


class DevicePanEntry(BaseModel):
    id: str
    label: str
    pan: str = Field(pattern=PAN_PATTERN)


class SyncDevicePansRequest(BaseModel):
    pans: list[DevicePanEntry]


class SubscriptionCategory(BaseModel):
    offered: int | None = None
    applied: int | None = None
    times: float | None = None


class IPOCatalogSummary(BaseModel):
    id: str
    company_name: str
    status: str
    open_date: date | None = None
    close_date: date | None = None
    # Basis-of-Allotment date -- when this IPO's allotment result actually
    # gets published, sourced from investorgain (see
    # ipo_catalog_service.refresh()'s primary source). Distinct from
    # listing_date (when the stock starts trading).
    boa_date: date | None = None
    price_band_low: float | None = None
    price_band_high: float | None = None
    issue_price: float | None = None
    lot_size: int | None = None
    issue_size_cr: float | None = None
    gmp_value: float | None = None
    gmp_percent: float | None = None
    listing_price: float | None = None
    current_price: float | None = None
    linked_registrar_ipo_id: str | None = None
    # Per-lot profit: real (current_price - issue_price) * lot_size once
    # listed, otherwise an *estimate* from GMP * lot_size -- GMP is an
    # unofficial grey-market number, not a guarantee, so profit_basis lets
    # the UI label the two very differently rather than presenting a
    # speculative pre-listing number with the same confidence as a real one.
    profit_per_lot: float | None = None
    profit_basis: str | None = None  # "actual" | "estimated"
    # Rule-based "should I apply" heuristic from GMP + subscription +
    # issue size -- fully explainable, not a black-box prediction, and
    # explicitly not investment advice (see ipo_catalog_service.compute_apply_signal).
    apply_signal: str | None = None  # "strong_apply" | "consider" | "skip"
    apply_signal_reason: str | None = None
    # Rough SEBI-lottery approximation (0-1) from retail subscription alone
    # -- not exact proportional-allotment math (see
    # ipo_catalog_service.compute_retail_allotment_probability).
    retail_allotment_probability: float | None = None
    # Oldest -> newest GMP% samples, capped by gmp_history_repository at 10.
    gmp_trend: list[float | None] | None = None
    # Deeper, multi-factor "IPO Potential" score -- news sentiment, broad
    # market trend, and REAL historical base-rate statistics from past
    # IPOs, distinct from (and additive to) apply_signal above. Explicitly
    # rule-based, not a trained model yet -- see
    # ipo_potential_service.py's module docstring for why. basis is always
    # "historical_stats" for now; "ml_model" is reserved for a future,
    # separately-gated phase once enough real outcomes exist.
    ipo_potential_label: str | None = None  # "strong_potential" | "promising" | "uncertain" | "weak"
    ipo_potential_score: int | None = None  # 0-100, display-only approximation, not a probability
    ipo_potential_reasons: list[str] | None = None
    ipo_potential_basis: str | None = None  # "historical_stats" | "ml_model"


class IPOCatalogDetail(IPOCatalogSummary):
    listing_date: date | None = None
    gmp_updated_at: datetime | None = None
    subscription_qib: SubscriptionCategory
    subscription_hni: SubscriptionCategory
    subscription_retail: SubscriptionCategory


class IPOCatalogListResponse(BaseModel):
    ipos: list[IPOCatalogSummary]
    generated_at: datetime


class NewsHeadline(BaseModel):
    title: str
    link: str | None = None
    source: str | None = None
    published_at: str | None = None


class NewsHeadlinesResponse(BaseModel):
    headlines: list[NewsHeadline]
    generated_at: datetime


class HistoricalOutcomeSummary(BaseModel):
    company_name: str
    listing_date: str | None = None
    issue_size_cr: float | None = None
    gmp_percent_at_close: float | None = None
    listing_gain_percent: float | None = None
    current_gain_percent: float | None = None


class SimilarOutcomesResponse(BaseModel):
    outcomes: list[HistoricalOutcomeSummary]
    generated_at: datetime


class SignalAccuracyBucket(BaseModel):
    total: int
    correct: int
    hit_rate: float | None


class TrackRecordResponse(BaseModel):
    total: int
    correct: int
    hit_rate: float | None
    by_signal: dict[str, SignalAccuracyBucket]
