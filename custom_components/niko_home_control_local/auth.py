"""Authentication helpers for Niko Hobby API tokens."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import json


def token_expiration(token: str) -> datetime | None:
    """Read the expiry timestamp from a JWT without validating its signature."""

    try:
        payload_part = token.split(".")[1]
        payload_part += "=" * (-len(payload_part) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_part).decode("utf-8"))
        return datetime.fromtimestamp(float(payload["exp"]), tz=timezone.utc)
    except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
