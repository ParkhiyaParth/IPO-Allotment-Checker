from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.enums import AllotmentStatus


@dataclass
class AllotmentResult:
    status: AllotmentStatus
    shares_allotted: int | None = None
    manual_check_url: str | None = None
    message: str | None = None


class RegistrarAdapter(ABC):
    registrar_name: str
    supports_automation: bool = True

    @abstractmethod
    async def check_status(self, pan: str, ipo_identifier: str) -> AllotmentResult:
        """Look up allotment status for a single PAN against a single IPO.

        ipo_identifier is registrar-specific (e.g. Link Intime's numeric
        clientid) — the caller resolves it from IPO metadata, adapters never
        need to know about other registrars' identifier formats.
        """
        raise NotImplementedError
