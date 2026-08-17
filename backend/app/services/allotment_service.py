from datetime import datetime, timezone

from app.models.enums import AllotmentStatus
from app.models.schemas import AllotmentResultItem, Applicant, CheckAllotmentResponse
from app.scrapers.registrars.registry import get_adapter
from app.services import ipo_list_service


class IpoNotFoundError(Exception):
    pass


async def check_allotment(ipo_id: str, applicants: list[Applicant]) -> CheckAllotmentResponse:
    ipo = ipo_list_service.get_by_id(ipo_id)
    if ipo is None:
        raise IpoNotFoundError(ipo_id)

    adapter = get_adapter(ipo.registrar)
    results: list[AllotmentResultItem] = []

    for applicant in applicants:
        if adapter is None:
            results.append(
                AllotmentResultItem(
                    pan=applicant.pan,
                    label=applicant.label,
                    status=AllotmentStatus.CHECK_FAILED,
                    message=f"Automated check not available yet for {ipo.registrar}.",
                )
            )
            continue

        outcome = await adapter.check_status(applicant.pan, ipo.registrar_ipo_identifier)
        results.append(
            AllotmentResultItem(
                pan=applicant.pan,
                label=applicant.label,
                status=outcome.status,
                shares_allotted=outcome.shares_allotted,
                manual_check_url=outcome.manual_check_url,
                message=outcome.message,
            )
        )

    return CheckAllotmentResponse(
        ipo_id=ipo_id,
        results=results,
        checked_at=datetime.now(timezone.utc),
    )
