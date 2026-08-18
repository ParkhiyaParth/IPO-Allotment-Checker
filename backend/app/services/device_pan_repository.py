"""SQLite-backed store of device-scoped, encrypted PANs for the opt-in
zero-tap allotment discovery feature. PAN values are already encrypted by
the time they reach this module (see device_pan_service.py + utils/encryption.py)
-- this module only ever handles ciphertext.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from app.db.database import get_connection


@dataclass
class DevicePan:
    id: str
    device_id: str
    label: str
    pan_encrypted: str
    created_at: str
    last_status: str | None = None
    last_checked_at: str | None = None


def replace_for_device(device_id: str, entries: list[tuple[str, str, str]]) -> None:
    """entries: (local_profile_id, label, pan_encrypted). Full replace-for-
    device on every sync call -- mirrors ipo_repository.prune_registrar's
    delete-not-in-keep-ids pattern, since the mobile app always sends its
    complete current PAN list, not incremental diffs."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        keep_ids = [f"{device_id}:{local_id}" for local_id, _, _ in entries]
        if keep_ids:
            placeholders = ", ".join("?" for _ in keep_ids)
            conn.execute(
                f"DELETE FROM device_pans WHERE device_id = ? AND id NOT IN ({placeholders})",
                (device_id, *keep_ids),
            )
        else:
            conn.execute("DELETE FROM device_pans WHERE device_id = ?", (device_id,))

        for local_id, label, pan_encrypted in entries:
            row_id = f"{device_id}:{local_id}"
            conn.execute(
                """
                INSERT INTO device_pans (id, device_id, label, pan_encrypted, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET label = excluded.label, pan_encrypted = excluded.pan_encrypted
                """,
                (row_id, device_id, label, pan_encrypted, now),
            )
        conn.commit()
    finally:
        conn.close()


def delete_for_device(device_id: str) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM device_pans WHERE device_id = ?", (device_id,))
        conn.commit()
    finally:
        conn.close()


def get_all() -> list[DevicePan]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM device_pans").fetchall()
    finally:
        conn.close()
    return [_row_to_record(row) for row in rows]


def update_last_result(pan_id: str, status: str, checked_at: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE device_pans SET last_status = ?, last_checked_at = ? WHERE id = ?",
            (status, checked_at, pan_id),
        )
        conn.commit()
    finally:
        conn.close()


def _row_to_record(row) -> DevicePan:
    return DevicePan(
        id=row["id"],
        device_id=row["device_id"],
        label=row["label"],
        pan_encrypted=row["pan_encrypted"],
        created_at=row["created_at"],
        last_status=row["last_status"],
        last_checked_at=row["last_checked_at"],
    )
