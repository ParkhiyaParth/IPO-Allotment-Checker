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
from datetime import date, datetime, timedelta, timezone

from app.scrapers.market_data import investorgain_client, nse_client
from app.services import (
    gmp_history_repository,
    ipo_catalog_repository,
    ipo_repository,
    push_service,
    signal_accuracy_repository,
)
from app.services.ipo_catalog_repository import CatalogRecord
from app.services.signal_accuracy_repository import SignalAccuracyEntry
from app.utils.name_matching import normalize_company_name

logger = logging.getLogger(__name__)

_STRONG_APPLY_SCORE = 4
_CONSIDER_SCORE = 1

_GMP_SWING_THRESHOLD_POINTS = 5.0
_GMP_SWING_WINDOW_HOURS = 6
_GMP_ALERT_COOLDOWN_HOURS = 6


def _subscription_times(offered: int | None, applied: int | None) -> float | None:
    if not offered or applied is None:
        return None
    return applied / offered


def compute_apply_signal(record: CatalogRecord) -> tuple[str | None, str | None]:
    """Rule-based, fully explainable "should I apply" estimate from GMP,
    subscription oversubscription, and issue size -- an unofficial
    heuristic, not investment advice. Returns (None, None) when there
    isn't enough data yet (e.g. an upcoming IPO before GMP appears)."""
    score = 0
    reasons: list[str] = []
    have_signal = False

    if record.gmp_percent is not None:
        have_signal = True
        gp = record.gmp_percent
        if gp >= 20:
            score += 2
        elif gp >= 5:
            score += 1
        elif gp < 0:
            score -= 2
        reasons.append(f"GMP {gp:+.0f}%")

    qib_times = _subscription_times(record.sub_qib_offered, record.sub_qib_applied)
    if qib_times is not None:
        have_signal = True
        if qib_times >= 10:
            score += 2
        elif qib_times >= 3:
            score += 1
        elif qib_times < 1:
            score -= 1
        reasons.append(f"QIB {qib_times:.1f}x")

    retail_times = _subscription_times(record.sub_retail_offered, record.sub_retail_applied)
    if retail_times is not None:
        have_signal = True
        if retail_times >= 5:
            score += 1
        elif retail_times < 1:
            score -= 1
        reasons.append(f"Retail {retail_times:.1f}x")

    if record.issue_size_cr is not None:
        if record.issue_size_cr < 100:
            score += 1
        elif record.issue_size_cr > 1000:
            score -= 1

    if not have_signal:
        return None, None

    if score >= _STRONG_APPLY_SCORE:
        label = "strong_apply"
    elif score >= _CONSIDER_SCORE:
        label = "consider"
    else:
        label = "skip"

    return label, ", ".join(reasons) if reasons else None


def compute_retail_allotment_probability(record: CatalogRecord) -> float | None:
    """Approximation of SEBI retail-lottery odds, using sub_retail_offered /
    sub_retail_applied as a proxy for lots-offered / applicants -- both are
    counted in the same subscription units, so the ratio approximates the
    odds even though applicants aren't literally 1 lot each (over- and
    under-lot bids roughly cancel out in aggregate). Not exact
    proportional-allotment math -- None when inputs aren't known yet."""
    if not record.sub_retail_offered or not record.sub_retail_applied:
        return None
    return min(1.0, record.sub_retail_offered / record.sub_retail_applied)


def _detect_gmp_swing(catalog_id: str, current_percent: float) -> float | None:
    """Compares current_percent against the oldest sample still inside the
    swing window. Must be called BEFORE this cycle's sample is appended to
    history, or it would end up comparing the new reading against itself."""
    samples = gmp_history_repository.get_recent(catalog_id)  # newest first
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_GMP_SWING_WINDOW_HOURS)
    in_window = [
        s for s in samples if s.gmp_percent is not None and datetime.fromisoformat(s.recorded_at) >= cutoff
    ]
    if not in_window:
        return None
    swing = current_percent - in_window[-1].gmp_percent
    return swing if abs(swing) >= _GMP_SWING_THRESHOLD_POINTS else None


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
            boa_date=row.boa_date,
            listing_date=row.listing_date,
            lot_size=row.lot_size,
            issue_size_cr=row.issue_size_cr,
            issue_price=row.issue_price,
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

        # NSE's real category names are full phrases ("Qualified
        # Institutional Buyers(QIBs)", "Non Institutional Investors",
        # "Retail Individual Investors(RIIs)") -- confirmed live -- not
        # short codes, so matching by "QIB"/"HNI"/"RETAIL" strings never
        # actually matched anything (always fell through to None/"-"). Sr.No
        # is far more robust: NSE always uses top-level "1"/"2"/"3" for
        # these three categories, with sub-breakdowns as "1(a)", "2.1" etc,
        # so this can't accidentally grab a subcategory's numbers instead.
        sub_by_sr_no = {s.sr_no: s for s in subscription}
        qib = sub_by_sr_no.get("1")
        hni = sub_by_sr_no.get("2")
        retail = sub_by_sr_no.get("3")

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

    # Consolidated per-record pass: one fetch of the record's *previous* row
    # feeds every "detect a one-time transition / periodic check" decision
    # below (apply-signal notify, signal-accuracy logging, GMP-momentum
    # alert) -- avoids both re-fetching per concern and one concern's early
    # exit accidentally skipping the others (e.g. a "skip"-signal IPO still
    # needs its GMP-swing check run).
    to_notify_apply_signal: list[tuple[CatalogRecord, str]] = []
    to_log_accuracy: list[SignalAccuracyEntry] = []
    to_notify_gmp_swing: list[tuple[CatalogRecord, float]] = []
    to_append_gmp_history: list[tuple[str, float]] = []

    for record_id, record in records.items():
        existing = ipo_catalog_repository.get_by_id(record_id)
        status = compute_status(record.open_date, record.close_date, date.today())
        signal, reason = compute_apply_signal(record)

        # Apply-signal notification: once per strong-apply streak -- not
        # re-sent every refresh while it stays strong, but sent again if it
        # drops out and later re-enters strong_apply.
        prev_notified = existing.notified_apply_signal if existing else ""
        if signal == "strong_apply":
            record.notified_apply_signal = "strong_apply"
            if status in ("open", "upcoming") and prev_notified != "strong_apply":
                to_notify_apply_signal.append((record, reason or ""))
        else:
            record.notified_apply_signal = ""

        # Signal-accuracy logging: once, the first time the real outcome is
        # knowable (closed + both prices present).
        prev_logged = existing.signal_accuracy_logged if existing else ""
        if (
            status == "closed"
            and record.current_price is not None
            and record.issue_price is not None
            and signal is not None
            and prev_logged != "yes"
        ):
            to_log_accuracy.append(
                SignalAccuracyEntry(
                    catalog_id=record.id,
                    company_name=record.company_name,
                    signal_at_close=signal,
                    was_profitable=(record.current_price - record.issue_price) > 0,
                    logged_at=now_iso,
                )
            )
            record.signal_accuracy_logged = "yes"
        else:
            record.signal_accuracy_logged = prev_logged

        # GMP-momentum alert: compare against history *before* this cycle's
        # sample is appended (history keeps accumulating either way).
        prev_alerted_at = existing.gmp_momentum_alerted_at if existing else ""
        if record.gmp_percent is not None:
            swing = _detect_gmp_swing(record_id, record.gmp_percent)
            cooldown_elapsed = not prev_alerted_at or (
                datetime.now(timezone.utc) - datetime.fromisoformat(prev_alerted_at)
                >= timedelta(hours=_GMP_ALERT_COOLDOWN_HOURS)
            )
            if swing is not None and cooldown_elapsed:
                record.gmp_momentum_alerted_at = now_iso
                to_notify_gmp_swing.append((record, swing))
            else:
                record.gmp_momentum_alerted_at = prev_alerted_at
            to_append_gmp_history.append((record_id, record.gmp_percent))
        else:
            record.gmp_momentum_alerted_at = prev_alerted_at

    if records:
        ipo_catalog_repository.upsert_many(list(records.values()))

    for record, reason in to_notify_apply_signal:
        await push_service.notify_apply_signal(record.company_name, reason, record.close_date)

    for entry in to_log_accuracy:
        signal_accuracy_repository.insert(entry)

    for catalog_id, gmp_percent in to_append_gmp_history:
        gmp_history_repository.append(catalog_id, gmp_percent)

    for record, swing in to_notify_gmp_swing:
        await push_service.notify_gmp_momentum(record.company_name, swing, record.gmp_percent or 0.0)

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
