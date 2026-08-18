from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.schemas import SyncDevicePansRequest
from app.services import device_pan_service
from app.services.device_pan_service import DevicePanEntry

router = APIRouter(prefix="/device-pans", tags=["device-pans"])


@router.put("/{device_id}", status_code=204)
async def sync_device_pans(device_id: str, request: SyncDevicePansRequest) -> None:
    if not settings.pan_encryption_key:
        raise HTTPException(503, "Server-side PAN storage isn't configured on this server yet.")
    entries = [DevicePanEntry(id=p.id, label=p.label, pan=p.pan) for p in request.pans]
    device_pan_service.sync_pans(device_id, entries)


@router.delete("/{device_id}", status_code=204)
async def delete_device_pans(device_id: str) -> None:
    device_pan_service.opt_out(device_id)
