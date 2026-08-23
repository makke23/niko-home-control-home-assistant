from __future__ import annotations

import base64
import json

from custom_components.niko_home_control_local.auth import token_expiration


def _part(value: dict[str, object]) -> str:
    return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")


def test_token_expiration_reads_jwt_exp() -> None:
    token = f"{_part({'alg': 'none'})}.{_part({'exp': 2000000000})}.signature"
    assert token_expiration(token).timestamp() == 2000000000


def test_token_expiration_rejects_invalid_token() -> None:
    assert token_expiration("not-a-jwt") is None
