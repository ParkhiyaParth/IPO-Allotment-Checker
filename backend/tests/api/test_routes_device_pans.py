import base64
import secrets

import pytest
from fastapi import HTTPException

from app.api.routes_device_pans import delete_device_pans, sync_device_pans
from app.config import settings
from app.models.schemas import DevicePanEntry, SyncDevicePansRequest
from app.services import device_pan_repository

_VALID_KEY = base64.b64encode(secrets.token_bytes(32)).decode()


async def test_sync_returns_503_when_encryption_key_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "pan_encryption_key", "")
    request = SyncDevicePansRequest(pans=[DevicePanEntry(id="pan-a", label="Alice", pan="ABCDE1234F")])

    with pytest.raises(HTTPException) as exc_info:
        await sync_device_pans("device-1", request)

    assert exc_info.value.status_code == 503


async def test_sync_stores_encrypted_pan(monkeypatch):
    monkeypatch.setattr(settings, "pan_encryption_key", _VALID_KEY)
    request = SyncDevicePansRequest(pans=[DevicePanEntry(id="pan-a", label="Alice", pan="ABCDE1234F")])

    await sync_device_pans("device-1", request)

    stored = device_pan_repository.get_all()
    assert len(stored) == 1
    assert stored[0].label == "Alice"
    assert stored[0].pan_encrypted != "ABCDE1234F"  # never stored in plaintext


async def test_delete_removes_all_pans_for_device(monkeypatch):
    monkeypatch.setattr(settings, "pan_encryption_key", _VALID_KEY)
    await sync_device_pans("device-1", SyncDevicePansRequest(pans=[DevicePanEntry(id="pan-a", label="Alice", pan="ABCDE1234F")]))

    await delete_device_pans("device-1")

    assert device_pan_repository.get_all() == []
