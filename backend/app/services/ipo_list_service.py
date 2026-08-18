"""Aggregates "IPOs available to check" across registrars into the cache.

Milestone 2 replaces the Milestone 1 hardcoded list with real data pulled
directly from each registrar's own "list of IPOs in the status-check
dropdown" — Link Intime's GetDetails call, Bigshare's rendered <select>,
and KFintech's bundled dropdown data (see the respective *_client.py
modules). Going straight to the registrars avoids depending on a
third-party aggregator's page structure (Chittorgarh/Investorgain both
turned out to be JS-rendered Next.js apps without a simple public data
endpoint) and is more robust: each registrar populates that dropdown with
exactly the IPOs it considers checkable right now.
"""

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone

from app.scrapers.registrars import bigshare_client, kfintech_client, linkintime_client
from app.services import ipo_catalog_repository, ipo_repository, push_service
from app.services.ipo_repository import CachedIpo

logger = logging.getLogger(__name__)

# Registrar dropdowns mix equity IPOs in with other instruments they also
# process status-checks for (NCDs/bonds, InvITs, etc.) — those aren't IPOs
# at all, regardless of allotment status, so they're filtered out here
# rather than left for the user to sort through.
_NON_IPO_PATTERN = re.compile(r"\b(NCDS?\d*|INVIT|BOND\d*|DEBENTURE)\b", re.IGNORECASE)


def _is_equity_ipo(company_name: str) -> bool:
    return not _NON_IPO_PATTERN.search(company_name)


@dataclass
class IPORecord:
    id: str
    company_name: str
    registrar: str
    registrar_ipo_identifier: str
    allotment_date: date
    listing_date: date | None
    automation_supported: bool


def _build_registrar_batch(
    registrar: str, items: list[tuple[str, str]], now_iso: str
) -> list[CachedIpo]:
    """items is a list of (registrar_identifier, company_name) tuples,
    already in that registrar's own list order (used as the recency rank)."""
    return [
        CachedIpo(
            id=f"{registrar}-{identifier}",
            company_name=name,
            registrar=registrar,
            registrar_ipo_identifier=identifier,
            automation_supported=True,
            first_seen_at=now_iso,
            list_rank=rank,
        )
        for rank, (identifier, name) in enumerate(items)
        if _is_equity_ipo(name)
    ]


async def refresh() -> int:
    """Pull each registrar's current IPO list and upsert into the cache.

    Returns the number of registrars that were reachable. Each registrar is
    independent — one failing (e.g. a site redesign) doesn't block the
    others from refreshing. Also detects genuinely new IPOs (not seen in any
    prior refresh) and fires a push notification for them.
    """
    is_first_ever_refresh = ipo_repository.is_empty()
    all_records: list[CachedIpo] = []
    newly_discovered_names: list[str] = []
    now_iso = datetime.now(timezone.utc).isoformat()
    ok_count = 0

    fetchers = [
        ("linkintime", lambda companies: [(c.company_id, c.company_name) for c in companies],
         linkintime_client.get_companies),
        ("bigshare", lambda companies: [(c.company_id, c.company_name) for c in companies],
         bigshare_client.get_active_companies),
        ("kfintech", lambda ipos: [(i.client_id, i.name) for i in ipos],
         kfintech_client.get_active_ipos),
    ]

    for registrar, to_pairs, fetch in fetchers:
        try:
            previously_known_ids = ipo_repository.get_ids_for_registrar(registrar)
            items = to_pairs(await fetch())
            batch = _build_registrar_batch(registrar, items, now_iso)

            for record in batch:
                if record.id not in previously_known_ids:
                    newly_discovered_names.append(record.company_name)

            all_records.extend(batch)
            ipo_repository.prune_registrar(registrar, [r.id for r in batch])
            ok_count += 1
        except Exception:
            logger.exception("%s IPO list refresh failed", registrar)

    if all_records:
        # first_seen_at is only meaningful the *first* time we see an id —
        # upsert_many preserves the original first_seen_at on conflict, so
        # passing "now" for every row here is safe: new rows get "now" as
        # their true first sighting, existing rows keep their real one.
        ipo_repository.upsert_many(all_records)

    # Skip notifying on the very first-ever refresh (empty cache) — that's
    # the entire existing catalog appearing at once, not "new" in any
    # meaningful sense, and would otherwise spam every saved device the
    # first time the backend starts up.
    if newly_discovered_names and not is_first_ever_refresh:
        await push_service.notify_new_ipos(newly_discovered_names)

    return ok_count


def get_recent(limit: int = 15) -> list[IPORecord]:
    return [_to_record(c) for c in ipo_repository.get_recent(limit)]


def get_by_id(ipo_id: str) -> IPORecord | None:
    cached = ipo_repository.get_by_id(ipo_id)
    return _to_record(cached) if cached else None


def _to_record(cached: CachedIpo) -> IPORecord:
    # The registrar cache itself has no real allotment-date field (see
    # module docstring) — but the catalog feature's investorgain source
    # publishes a real Basis-of-Allotment date, and links to this exact
    # cache row via linked_registrar_ipo_id when it recognizes the company.
    # Use that real date whenever it's available; only fall back to the
    # first-seen proxy for IPOs the catalog hasn't matched (yet).
    catalog_entry = ipo_catalog_repository.get_by_linked_registrar_id(cached.id)
    if catalog_entry and catalog_entry.boa_date:
        allotment_date = date.fromisoformat(catalog_entry.boa_date)
    else:
        allotment_date = datetime.fromisoformat(cached.first_seen_at).date()

    listing_date = (
        date.fromisoformat(catalog_entry.listing_date)
        if catalog_entry and catalog_entry.listing_date
        else None
    )

    return IPORecord(
        id=cached.id,
        company_name=cached.company_name,
        registrar=cached.registrar,
        registrar_ipo_identifier=cached.registrar_ipo_identifier,
        allotment_date=allotment_date,
        listing_date=listing_date,
        automation_supported=cached.automation_supported,
    )
