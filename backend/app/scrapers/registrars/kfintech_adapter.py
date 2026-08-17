import logging

from app.models.enums import AllotmentStatus
from app.scrapers.registrars import kfintech_client
from app.scrapers.registrars.base import AllotmentResult, RegistrarAdapter

logger = logging.getLogger(__name__)

MANUAL_CHECK_URL = "https://ipostatus.kfintech.com/"


def _collect_keys(data: object, prefix: str = "") -> list[str]:
    """Field names only, at any depth — never values (may carry PII)."""
    keys: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            keys.append(path)
            keys.extend(_collect_keys(value, path))
    elif isinstance(data, list) and data:
        keys.extend(_collect_keys(data[0], f"{prefix}[0]"))
    return keys


class KfintechAdapter(RegistrarAdapter):
    registrar_name = "kfintech"
    supports_automation = True

    async def check_status(self, pan: str, ipo_identifier: str) -> AllotmentResult:
        try:
            result = await kfintech_client.search_by_pan(ipo_identifier, pan)
        except Exception:  # noqa: BLE001 - any network/parse failure degrades gracefully
            logger.exception("KFintech check failed for ipo=%s", ipo_identifier)
            return AllotmentResult(
                status=AllotmentStatus.CHECK_FAILED,
                manual_check_url=MANUAL_CHECK_URL,
                message="Could not reach KFintech right now.",
            )

        if not result.found:
            return AllotmentResult(status=AllotmentStatus.NOT_APPLIED, manual_check_url=MANUAL_CHECK_URL)

        allotted = result.shares_allotted
        if allotted is None:
            # Found a record but couldn't confidently parse an allotted-shares
            # field from the response shape — surface it rather than guess.
            # Log field *names* only (never values — they can carry the
            # applicant's name/application number) so the parser can be
            # fixed to match KFintech's real "found" response shape.
            logger.warning(
                "KFintech found a record for ipo=%s but no recognizable "
                "allotment field; response keys (all depths)=%s",
                ipo_identifier,
                _collect_keys(result.raw),
            )
            return AllotmentResult(
                status=AllotmentStatus.CHECK_FAILED,
                manual_check_url=MANUAL_CHECK_URL,
                message="Couldn't confidently parse this result.",
            )

        if allotted > 0:
            return AllotmentResult(
                status=AllotmentStatus.ALLOTTED,
                shares_allotted=allotted,
                manual_check_url=MANUAL_CHECK_URL,
            )
        return AllotmentResult(
            status=AllotmentStatus.NOT_ALLOTTED,
            shares_allotted=0,
            manual_check_url=MANUAL_CHECK_URL,
        )
