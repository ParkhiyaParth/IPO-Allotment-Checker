import logging

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("client_diagnostics")

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


class DiagnosticEvent(BaseModel):
    message: str


@router.post("", status_code=204)
async def report_diagnostic(event: DiagnosticEvent) -> None:
    logger.info("CLIENT: %s", event.message)
