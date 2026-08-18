"""Aggregates NSE calendar/subscription data and Chittorgarh GMP data into
the ipo_catalog cache, linking each entry to the existing registrar-based
ipo_cache by normalized company name so the mobile app can offer an
Allotment-check button only where that link exists.

Each source is fetched independently -- one failing (site redesign, rate
limit, network blip) never blocks the other or discards previously-cached
values for fields it doesn't currently supply (see
ipo_catalog_repository.upsert_many's COALESCE-based merge).
"""

import logging
from datetime import date, datetime, timezone

from app.scrapers.market_data import investorgain_client, nse_client
from app.services import ipo_catalog_repository, ipo_repository
from app.services.ipo_catalog_repository import CatalogRecord
from app.utils.name_matching import normalize_company_name

logger = logging.getLogger(__name__)


def compute_status(open_date: str | None, close_date: str | None, today: date) -> str:
    parsed_open = date.fromisoformat(open_date) if open_date else None
    parsed_close = date.fromisoformat(close_date) if close_date else None

    if parsed_open is not None and today < parsed_open:
        return "upcoming"
    if parsed_close is not None and today > parsed_close:
        return "closed"
    if parsed_open is None:
        return "upcoming"
    return "open"


def _catalog_id(company_name: str) -> str:
    return f"catalog-{normalize_company_name(company_name).replace(' ', '-').lower()}"


async def refresh() -> int:
    now_iso = datetime.now(timezone.utc).isoformat()
    ok_count = 0
    records: dict[str, CatalogRecord] = {}

    registrar_by_name = {
        normalize_company_name(r.company_name): r.id for r in ipo_repository.get_all()
    }

    # investorgain is the primary source: unlike NSE's current-issue feed
    # (open bidding only, no lot size at all), this one covers upcoming,
    # open, closed, and already-listed IPOs in one call, each with a lot
    # size and clean ISO calendar dates.
    try:
        ig_rows = await investorgain_client.get_live_report()
        ok_count += 1
    except Exception:
        logger.exception("investorgain GMP/calendar refresh failed")
        ig_rows = []

    for row in ig_rows:
        normalized = normalize_company_name(row.company_name)
        record_id = _catalog_id(row.company_name)
        records[record_id] = CatalogRecord(
            id=record_id,
            company_name=row.company_name,
            open_date=row.open_date,
            close_date=row.close_date,
            listing_date=row.listing_date,
            lot_size=row.lot_size,
            issue_size_cr=row.issue_size_cr,
            gmp_value=row.gmp_value,
            gmp_percent=row.gmp_percent,
            gmp_updated_at=now_iso if row.gmp_value is not None else None,
            linked_registrar_ipo_id=registrar_by_name.get(normalized),
            first_seen_at=now_iso,
        )

    # NSE supplements investorgain with subscription-by-category (QIB/HNI/
    # Retail) and the price band, neither of which investorgain's report
    # exposes broken down. Only ever *adds* to a record investorgain
    # already produced, or seeds calendar fields for something investorgain
    # doesn't have this cycle -- investorgain's own dates never get
    # overwritten by less-complete NSE data.
    try:
        issues = await nse_client.get_current_issues()
        ok_count += 1
    except Exception:
        logger.exception("NSE IPO calendar refresh failed")
        issues = []

    for issue in issues:
        normalized = normalize_company_name(issue.company_name)
        record_id = _catalog_id(issue.company_name)

        subscription: list = []
        try:
            subscription = await nse_client.get_subscription(issue.symbol)
        except Exception:
            logger.exception("NSE subscription fetch failed for %s", issue.symbol)

        sub_by_category = {s.category.upper(): s for s in subscription}
        qib = sub_by_category.get("QIB")
        hni = sub_by_category.get("HNI") or sub_by_category.get("NII")
        retail = sub_by_category.get("RETAIL") or sub_by_category.get("RII")

        target = records.get(record_id) or CatalogRecord(
            id=record_id,
            company_name=issue.company_name,
            open_date=issue.open_date,
            close_date=issue.close_date,
            linked_registrar_ipo_id=registrar_by_name.get(normalized),
            first_seen_at=now_iso,
        )
        target.nse_symbol = issue.symbol
        target.price_band_low = issue.price_band_low
        target.price_band_high = issue.price_band_high
        if target.lot_size is None:
            target.lot_size = issue.lot_size
        if target.issue_size_cr is None:
            target.issue_size_cr = issue.issue_size_cr
        target.sub_qib_offered = qib.offered if qib else None
        target.sub_qib_applied = qib.applied if qib else None
        target.sub_hni_offered = hni.offered if hni else None
        target.sub_hni_applied = hni.applied if hni else None
        target.sub_retail_offered = retail.offered if retail else None
        target.sub_retail_applied = retail.applied if retail else None
        target.sub_updated_at = now_iso if subscription else target.sub_updated_at
        records[record_id] = target

    # IPOs no longer in NSE's current-issue feed (bidding closed, dropped
    # from that endpoint) still need a current price so the mobile app can
    # show listing vs current price. The first successfully captured price
    # also seeds listing_price as a best-effort proxy for the actual
    # listing-day price, since NSE's public API doesn't expose a dedicated
    # "listing price" field separate from the live quote.
    for existing in ipo_catalog_repository.get_all():
        if not existing.nse_symbol:
            continue
        if compute_status(existing.open_date, existing.close_date, date.today()) != "closed":
            continue
        try:
            price = await nse_client.get_quote(existing.nse_symbol)
        except Exception:
            logger.exception("NSE quote fetch failed for %s", existing.nse_symbol)
            continue
        if price is None:
            continue
        target = records.get(existing.id) or CatalogRecord(
            id=existing.id, company_name=existing.company_name, first_seen_at=existing.first_seen_at
        )
        target.current_price = price
        target.current_price_updated_at = now_iso
        if existing.listing_price is None and target.listing_price is None:
            target.listing_price = price
        records[existing.id] = target

    if records:
        ipo_catalog_repository.upsert_many(list(records.values()))

    return ok_count


def get_by_status(status: str) -> list[CatalogRecord]:
    today = date.today()
    return [
        r
        for r in ipo_catalog_repository.get_all()
        if compute_status(r.open_date, r.close_date, today) == status
    ]


def get_by_id(catalog_id: str) -> CatalogRecord | None:
    return ipo_catalog_repository.get_by_id(catalog_id)
