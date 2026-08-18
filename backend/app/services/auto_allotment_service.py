"""Runs the same registrar-check flow as allotment_service.py, but
unattended -- triggered once per IPO from ipo_catalog_service.refresh() the
moment its boa_date is reached, against every opted-in device's saved
PANs, pushing the result to that device instead of returning it in an API
response. Nothing here is watched synchronously, so every failure is
logged and skipped rather than raised.
"""

import asyncio
import logging
from datetime import datetime, timezone

from app.scrapers.registrars.registry import get_adapter
from app.services import device_pan_repository, ipo_list_service, push_service
from app.utils import encryption

logger = logging.getLogger(__name__)

# allotment_service.py (the live, user-watched check) has zero throttling --
# fine for one small batch with a user waiting. This runs in the background
# against every saved device PAN with nobody watching, so it gets its own
# modest concurrency cap per registrar instead.
_MAX_CONCURRENT_CHECKS_PER_REGISTRAR = 4
_semaphores: dict[str, asyncio.Semaphore] = {}


def _semaphore_for(registrar: str) -> asyncio.Semaphore:
    if registrar not in _semaphores:
        _semaphores[registrar] = asyncio.Semaphore(_MAX_CONCURRENT_CHECKS_PER_REGISTRAR)
    return _semaphores[registrar]


async def run_auto_checks_for_ipo(registrar_ipo_id: str) -> None:
    ipo = ipo_list_service.get_by_id(registrar_ipo_id)
    if ipo is None:
        return

    adapter = get_adapter(ipo.registrar)
    if adapter is None:
        return

    all_pans = device_pan_repository.get_all()
    if not all_pans:
        return

    sem = _semaphore_for(ipo.registrar)

    async def _check_one(dp) -> None:
        async with sem:
            try:
                plaintext_pan = encryption.decrypt_pan(dp.pan_encrypted)
            except Exception:
                logger.exception("Failed to decrypt device_pan %s", dp.id)
                return
            try:
                result = await adapter.check_status(plaintext_pan, ipo.registrar_ipo_identifier)
                device_pan_repository.update_last_result(
                    dp.id, result.status.value, datetime.now(timezone.utc).isoformat()
                )
                await push_service.notify_allotment_result(dp.device_id, ipo.company_name, result)
            except Exception:
                logger.exception("Auto allotment check failed for device_pan %s", dp.id)

    await asyncio.gather(*[_check_one(dp) for dp in all_pans])
