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


class IPOCatalogDetail(IPOCatalogSummary):
    listing_date: date | None = None
    gmp_updated_at: datetime | None = None
    subscription_qib: SubscriptionCategory
    subscription_hni: SubscriptionCategory
    subscription_retail: SubscriptionCategory


class IPOCatalogListResponse(BaseModel):
    ipos: list[IPOCatalogSummary]
    generated_at: datetime
