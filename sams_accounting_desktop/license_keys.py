from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization


PRODUCT = "sams-accounting-desktop"


@dataclass(frozen=True)
class LicenseClaims:
    customer: str
    expires: date
    licence_id: str


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def public_key_path() -> Path:
    return Path(__file__).resolve().parent / "assets" / "license-public.pem"


def validate_signed_license(value: str, *, today: date | None = None) -> tuple[bool, str, LicenseClaims | None]:
    token = value.strip()
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != "SAM1":
        return False, "Use a valid signed licence key supplied by The Jishu IT Solution.", None
    try:
        payload_bytes = _decode(parts[1])
        signature = _decode(parts[2])
        public_key = serialization.load_pem_public_key(public_key_path().read_bytes())
        public_key.verify(signature, payload_bytes)
        payload = json.loads(payload_bytes.decode("utf-8"))
        expires = date.fromisoformat(payload["expires"])
        if payload.get("product") != PRODUCT:
            return False, "This licence is for a different product.", None
        if expires < (today or date.today()):
            return False, f"This licence expired on {expires.isoformat()}.", None
        claims = LicenseClaims(
            customer=str(payload.get("customer", "")).strip(),
            expires=expires,
            licence_id=str(payload.get("licence_id", "")).strip(),
        )
        if not claims.customer or not claims.licence_id:
            return False, "The licence payload is incomplete.", None
        return True, f"Licence valid through {expires.isoformat()}.", claims
    except (OSError, ValueError, KeyError, json.JSONDecodeError, InvalidSignature):
        return False, "Licence signature verification failed.", None
