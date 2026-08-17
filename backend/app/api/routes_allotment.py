from fastapi import APIRouter, HTTPException

from app.models.schemas import CheckAllotmentRequest, CheckAllotmentResponse
from app.services import allotment_service
from app.services.allotment_service import IpoNotFoundError

router = APIRouter(prefix="/ipos", tags=["allotment"])


@router.post("/{ipo_id}/check-allotment", response_model=CheckAllotmentResponse)
async def check_allotment(ipo_id: str, request: CheckAllotmentRequest) -> CheckAllotmentResponse:
    try:
        return await allotment_service.check_allotment(ipo_id, request.applicants)
    except IpoNotFoundError as exc:
        raise HTTPException(status_code=404, detail="IPO not found") from exc
