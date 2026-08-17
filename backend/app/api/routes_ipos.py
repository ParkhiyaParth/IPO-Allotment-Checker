from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.models.schemas import IPOSummary, RecentIposResponse
from app.services import ipo_list_service

router = APIRouter(prefix="/ipos", tags=["ipos"])


@router.get("/recent", response_model=RecentIposResponse)
async def get_recent_ipos() -> RecentIposResponse:
    records = ipo_list_service.get_recent()
    return RecentIposResponse(
        ipos=[
            IPOSummary(
                id=r.id,
                company_name=r.company_name,
                registrar=r.registrar,
                allotment_date=r.allotment_date,
                listing_date=r.listing_date,
                automation_supported=r.automation_supported,
            )
            for r in records
        ],
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/{ipo_id}", response_model=IPOSummary)
async def get_ipo(ipo_id: str) -> IPOSummary:
    record = ipo_list_service.get_by_id(ipo_id)
    if record is None:
        raise HTTPException(status_code=404, detail="IPO not found")
    return IPOSummary(
        id=record.id,
        company_name=record.company_name,
        registrar=record.registrar,
        allotment_date=record.allotment_date,
        listing_date=record.listing_date,
        automation_supported=record.automation_supported,
    )
