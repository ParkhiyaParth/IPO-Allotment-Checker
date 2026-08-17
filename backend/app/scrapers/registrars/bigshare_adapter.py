import logging

from app.models.enums import AllotmentStatus
from app.scrapers.registrars import bigshare_client
from app.scrapers.registrars.base import AllotmentResult, RegistrarAdapter
from app.utils.parsing import to_int

logger = logging.getLogger(__name__)

MANUAL_CHECK_URL = "https://ipo.bigshareonline.com/IPO_Status.html"


class BigshareAdapter(RegistrarAdapter):
    registrar_name = "bigshare"
    supports_automation = True

    async def check_status(self, pan: str, ipo_identifier: str) -> AllotmentResult:
        try:
            result = await bigshare_client.search_by_pan(ipo_identifier, pan)
        except Exception:  # noqa: BLE001 - any network/parse failure degrades gracefully
            logger.exception("Bigshare check failed for ipo=%s", ipo_identifier)
            return AllotmentResult(
                status=AllotmentStatus.CHECK_FAILED,
                manual_check_url=MANUAL_CHECK_URL,
                message="Could not reach Bigshare right now.",
            )

        if not result.found:
            return AllotmentResult(status=AllotmentStatus.NOT_APPLIED, manual_check_url=MANUAL_CHECK_URL)

        allotted = to_int(result.allotted)
        if allotted is None:
            # A record was found but the "allotted" field wasn't a plain
            # number — don't silently treat that as "0 allotted", surface it
            # instead. Safe to log: this is a share-count/status field, not
            # the applicant's name or DP ID.
            logger.warning(
                "Bigshare found a record for ipo=%s but ALLOTED field wasn't numeric: %r",
                ipo_identifier,
                result.allotted,
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
