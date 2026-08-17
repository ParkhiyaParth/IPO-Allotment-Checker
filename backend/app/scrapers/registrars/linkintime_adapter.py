import logging

from app.models.enums import AllotmentStatus
from app.scrapers.registrars import linkintime_client
from app.scrapers.registrars.base import AllotmentResult, RegistrarAdapter

logger = logging.getLogger(__name__)

MANUAL_CHECK_URL = "https://in.mpms.mufg.com/Initial_Offer/public-issues.html"


class LinkIntimeAdapter(RegistrarAdapter):
    registrar_name = "linkintime"
    supports_automation = True

    async def check_status(self, pan: str, ipo_identifier: str) -> AllotmentResult:
        try:
            result = await linkintime_client.search_by_pan(ipo_identifier, pan)
        except Exception:  # noqa: BLE001 - any network/parse failure degrades gracefully
            logger.exception("Link Intime check failed for ipo=%s", ipo_identifier)
            return AllotmentResult(
                status=AllotmentStatus.CHECK_FAILED,
                manual_check_url=MANUAL_CHECK_URL,
                message="Could not reach Link Intime right now.",
            )

        if result.records:
            record = result.records[0]
            allotted = record.shares_allotted or 0
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

        if result.message:
            # A registrar-level message with no application row — treat as
            # inconclusive rather than assuming "not applied", since the exact
            # wording used for real error cases hasn't been observed yet.
            logger.warning(
                "Link Intime returned a message with no records for ipo=%s: %r",
                ipo_identifier,
                result.message,
            )
            return AllotmentResult(
                status=AllotmentStatus.CHECK_FAILED,
                manual_check_url=MANUAL_CHECK_URL,
                message=result.message,
            )

        return AllotmentResult(
            status=AllotmentStatus.NOT_APPLIED,
            manual_check_url=MANUAL_CHECK_URL,
        )
