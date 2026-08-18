import base64
import secrets
from datetime import date

from app.config import settings
from app.models.enums import AllotmentStatus
from app.scrapers.registrars.base import AllotmentResult
from app.services import auto_allotment_service, device_pan_repository, push_token_repository
from app.services.ipo_list_service import IPORecord
from app.utils import encryption

_VALID_KEY = base64.b64encode(secrets.token_bytes(32)).decode()


class _FakeAdapter:
    def __init__(self, result: AllotmentResult):
        self.result = result
        self.calls: list[tuple[str, str]] = []

    async def check_status(self, pan: str, ipo_identifier: str) -> AllotmentResult:
        self.calls.append((pan, ipo_identifier))
        return self.result


def _ipo_record(**overrides) -> IPORecord:
    defaults = dict(
        id="linkintime-1",
        company_name="Acme Ltd",
        registrar="linkintime",
        registrar_ipo_identifier="42",
        allotment_date=date(2026, 8, 18),
        listing_date=None,
        automation_supported=True,
    )
    defaults.update(overrides)
    return IPORecord(**defaults)


async def test_checks_every_saved_pan_and_notifies_owning_device(monkeypatch):
    monkeypatch.setattr(settings, "pan_encryption_key", _VALID_KEY)
    device_pan_repository.replace_for_device("device-1", [("pan-a", "Alice", encryption.encrypt_pan("ABCDE1234F"))])
    push_token_repository.register("ExponentPushToken[abc]", "device-1")

    fake_adapter = _FakeAdapter(AllotmentResult(status=AllotmentStatus.ALLOTTED, shares_allotted=10))
    monkeypatch.setattr(
        auto_allotment_service, "get_adapter", lambda name: fake_adapter if name == "linkintime" else None
    )
    monkeypatch.setattr(
        auto_allotment_service.ipo_list_service, "get_by_id", lambda ipo_id: _ipo_record(id=ipo_id)
    )

    sent = []

    async def _fake_notify(device_id, company_name, result):
        sent.append((device_id, company_name, result))

    monkeypatch.setattr(auto_allotment_service.push_service, "notify_allotment_result", _fake_notify)

    await auto_allotment_service.run_auto_checks_for_ipo("linkintime-1")

    assert fake_adapter.calls == [("ABCDE1234F", "42")]
    assert sent == [("device-1", "Acme Ltd", fake_adapter.result)]
    updated = device_pan_repository.get_all()[0]
    assert updated.last_status == "ALLOTTED"


async def test_returns_quietly_when_ipo_not_found(monkeypatch):
    monkeypatch.setattr(auto_allotment_service.ipo_list_service, "get_by_id", lambda ipo_id: None)

    await auto_allotment_service.run_auto_checks_for_ipo("does-not-exist")  # must not raise


async def test_returns_quietly_when_no_adapter_for_registrar(monkeypatch):
    monkeypatch.setattr(auto_allotment_service.ipo_list_service, "get_by_id", lambda ipo_id: _ipo_record())
    monkeypatch.setattr(auto_allotment_service, "get_adapter", lambda name: None)

    await auto_allotment_service.run_auto_checks_for_ipo("linkintime-1")  # must not raise


async def test_one_pans_check_failure_does_not_block_others(monkeypatch):
    monkeypatch.setattr(settings, "pan_encryption_key", _VALID_KEY)
    device_pan_repository.replace_for_device(
        "device-1",
        [
            ("pan-a", "Alice", encryption.encrypt_pan("ABCDE1234F")),
            ("pan-b", "Bob", encryption.encrypt_pan("FGHIJ5678K")),
        ],
    )

    class _FlakyAdapter:
        async def check_status(self, pan: str, ipo_identifier: str) -> AllotmentResult:
            if pan == "ABCDE1234F":
                raise RuntimeError("registrar site is down")
            return AllotmentResult(status=AllotmentStatus.NOT_ALLOTTED)

    monkeypatch.setattr(auto_allotment_service, "get_adapter", lambda name: _FlakyAdapter())
    monkeypatch.setattr(auto_allotment_service.ipo_list_service, "get_by_id", lambda ipo_id: _ipo_record())

    async def _noop_notify(*args, **kwargs):
        return None

    monkeypatch.setattr(auto_allotment_service.push_service, "notify_allotment_result", _noop_notify)

    await auto_allotment_service.run_auto_checks_for_ipo("linkintime-1")  # must not raise

    statuses = {p.label: p.last_status for p in device_pan_repository.get_all()}
    assert statuses["Bob"] == "NOT_ALLOTTED"
    assert statuses["Alice"] is None  # the failed check never got to update_last_result
