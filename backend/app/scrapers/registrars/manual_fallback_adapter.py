"""Shared adapter for registrars we haven't reverse-engineered yet.

Cameo (Angular SPA) and Skyline/Purva weren't investigated in depth — unlike
Link Intime and Bigshare, whose real AJAX endpoints turned out not to check
captchas at all, these would need their own discovery pass. Until then they
report CHECK_FAILED with a link to check manually, same as the graceful
degradation KFintech uses when its bot-detection challenge blocks it.
"""

from app.models.enums import AllotmentStatus
from app.scrapers.registrars.base import AllotmentResult, RegistrarAdapter


class ManualFallbackAdapter(RegistrarAdapter):
    def __init__(self, registrar_name: str, manual_check_url: str):
        self.registrar_name = registrar_name
        self.manual_check_url = manual_check_url
        self.supports_automation = False

    async def check_status(self, pan: str, ipo_identifier: str) -> AllotmentResult:
        return AllotmentResult(
            status=AllotmentStatus.CHECK_FAILED,
            manual_check_url=self.manual_check_url,
            message=f"Automated check isn't available for {self.registrar_name} yet — check manually.",
        )
