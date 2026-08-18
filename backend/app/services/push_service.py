"""Sends push notifications via Expo's push API.

Expo's push service relays to FCM (Android) / APNs (iOS) on our behalf, so
this backend never talks to Google/Apple directly — just a plain HTTPS POST
to Expo with the recipient's Expo push token.
"""

import logging

from app.services import push_token_repository
from app.utils.http_client import get_http_client

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
# Expo caps a single push request at 100 recipients.
_BATCH_SIZE = 100


async def notify_new_ipos(company_names: list[str]) -> None:
    if not company_names:
        return

    if len(company_names) == 1:
        title = "IPO allotment is out"
        body = f"{company_names[0]} — check your PANs now."
    else:
        title = f"{len(company_names)} new IPO allotments are out"
        body = ", ".join(company_names[:3]) + ("…" if len(company_names) > 3 else "")

    await _send_to_all(title, body)


async def notify_apply_signal(company_name: str, reason: str, close_date: str | None) -> None:
    title = f"Strong apply signal: {company_name}"
    deadline = f" Closes {close_date}." if close_date else ""
    body = f"{reason}.{deadline} Unofficial estimate, not investment advice."
    await _send_to_all(title, body)


async def _send_to_all(title: str, body: str) -> None:
    tokens = push_token_repository.get_all()
    if not tokens:
        return

    client = get_http_client()
    for i in range(0, len(tokens), _BATCH_SIZE):
        batch = tokens[i : i + _BATCH_SIZE]
        messages = [{"to": token, "title": title, "body": body, "sound": "default"} for token in batch]
        try:
            resp = await client.post(EXPO_PUSH_URL, json=messages)
            resp.raise_for_status()
        except Exception:
            logger.exception("Failed to send push notification batch")
