from datetime import date, datetime, timezone

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    IPOCatalogDetail,
    IPOCatalogListResponse,
    IPOCatalogSummary,
    IPOSummary,
    RecentIposResponse,
    SubscriptionCategory,
)
from app.services import ipo_catalog_service, ipo_list_service
from app.services.ipo_catalog_repository import CatalogRecord

router = APIRouter(prefix="/ipos", tags=["ipos"])

_VALID_STATUSES = {"open", "upcoming", "closed"}


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


def _profit_per_lot(record: CatalogRecord) -> tuple[float | None, str | None]:
    """Real profit once listed (needs both a live price and the issue
    price to compare against); otherwise an *estimate* from GMP alone,
    which needs no issue price since GMP is already the premium-per-share
    figure. Returns (None, None) when neither is available."""
    if record.current_price is not None and record.issue_price is not None and record.lot_size:
        return (record.current_price - record.issue_price) * record.lot_size, "actual"
    if record.gmp_value is not None and record.lot_size:
        return record.gmp_value * record.lot_size, "estimated"
    return None, None


def _to_summary(record: CatalogRecord, status: str) -> IPOCatalogSummary:
    profit_per_lot, profit_basis = _profit_per_lot(record)
    apply_signal, apply_signal_reason = ipo_catalog_service.compute_apply_signal(record)
    return IPOCatalogSummary(
        id=record.id,
        company_name=record.company_name,
        status=status,
        open_date=record.open_date,
        close_date=record.close_date,
        price_band_low=record.price_band_low,
        price_band_high=record.price_band_high,
        issue_price=record.issue_price,
        lot_size=record.lot_size,
        issue_size_cr=record.issue_size_cr,
        gmp_value=record.gmp_value,
        gmp_percent=record.gmp_percent,
        listing_price=record.listing_price,
        current_price=record.current_price,
        linked_registrar_ipo_id=record.linked_registrar_ipo_id,
        profit_per_lot=profit_per_lot,
        profit_basis=profit_basis,
        apply_signal=apply_signal,
        apply_signal_reason=apply_signal_reason,
    )


@router.get("/catalog", response_model=IPOCatalogListResponse)
async def get_ipo_catalog(status: str) -> IPOCatalogListResponse:
    if status not in _VALID_STATUSES:
        raise HTTPException(status_code=422, detail="status must be one of: open, upcoming, closed")
    records = ipo_catalog_service.get_by_status(status)
    return IPOCatalogListResponse(
        ipos=[_to_summary(r, status) for r in records],
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/catalog/{catalog_id}", response_model=IPOCatalogDetail)
async def get_ipo_catalog_detail(catalog_id: str) -> IPOCatalogDetail:
    record = ipo_catalog_service.get_by_id(catalog_id)
    if record is None:
        raise HTTPException(status_code=404, detail="IPO not found")
    status = ipo_catalog_service.compute_status(record.open_date, record.close_date, date.today())
    summary = _to_summary(record, status)
    return IPOCatalogDetail(
        **summary.model_dump(),
        listing_date=record.listing_date,
        gmp_updated_at=record.gmp_updated_at,
        subscription_qib=SubscriptionCategory(
            offered=record.sub_qib_offered,
            applied=record.sub_qib_applied,
            times=(record.sub_qib_applied / record.sub_qib_offered) if record.sub_qib_offered else None,
        ),
        subscription_hni=SubscriptionCategory(
            offered=record.sub_hni_offered,
            applied=record.sub_hni_applied,
            times=(record.sub_hni_applied / record.sub_hni_offered) if record.sub_hni_offered else None,
        ),
        subscription_retail=SubscriptionCategory(
            offered=record.sub_retail_offered,
            applied=record.sub_retail_applied,
            times=(record.sub_retail_applied / record.sub_retail_offered) if record.sub_retail_offered else None,
        ),
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
