from datetime import datetime, timezone

from app.db.database import get_connection


def register(token: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO push_tokens (token, registered_at) VALUES (?, ?) "
            "ON CONFLICT(token) DO NOTHING",
            (token, datetime.now(timezone.utc).isoformat()),
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
