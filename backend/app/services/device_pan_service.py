from dataclasses import dataclass

from app.services import device_pan_repository
from app.utils import encryption


@dataclass
class DevicePanEntry:
    id: str
    label: str
    pan: str


def sync_pans(device_id: str, entries: list[DevicePanEntry]) -> None:
    packed = [(e.id, e.label, encryption.encrypt_pan(e.pan)) for e in entries]
    device_pan_repository.replace_for_device(device_id, packed)


def opt_out(device_id: str) -> None:
    device_pan_repository.delete_for_device(device_id)
