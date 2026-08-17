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
