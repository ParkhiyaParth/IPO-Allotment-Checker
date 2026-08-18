from datetime import datetime, timezone

from app.db.database import get_connection


def register(token: str, device_id: str | None = None) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO push_tokens (token, registered_at, device_id) VALUES (?, ?, ?)
            ON CONFLICT(token) DO UPDATE SET device_id = excluded.device_id
            """,
            (token, datetime.now(timezone.utc).isoformat(), device_id or ""),
        )
        conn.commit()
    finally:
        conn.close()


def get_all() -> list[str]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT token FROM push_tokens").fetchall()
        return [row["token"] for row in rows]
    finally:
        conn.close()


def get_by_device_id(device_id: str) -> list[str]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT token FROM push_tokens WHERE device_id = ?", (device_id,)).fetchall()
        return [row["token"] for row in rows]
    finally:
        conn.close()
