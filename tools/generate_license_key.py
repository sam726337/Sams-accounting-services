from __future__ import annotations

import argparse
import base64
from datetime import date, timedelta
import json
from pathlib import Path
import secrets

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


PRODUCT = "sams-accounting-desktop"


def encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def initialise(private_path: Path, public_path: Path) -> None:
    if private_path.exists() or public_path.exists():
        raise SystemExit("Refusing to overwrite an existing licence key file.")
    private_key = Ed25519PrivateKey.generate()
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    print(f"Private key created: {private_path}")
    print(f"Public key created: {public_path}")


def issue(private_path: Path, customer: str, days: int, licence_id: str) -> str:
    private_key = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
    payload = {
        "customer": " ".join(customer.split()),
        "expires": (date.today() + timedelta(days=days)).isoformat(),
        "licence_id": licence_id or secrets.token_hex(6).upper(),
        "product": PRODUCT,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = private_key.sign(payload_bytes)
    return f"SAM1.{encode(payload_bytes)}.{encode(signature)}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate signed Sams Accounting Desktop licences.")
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--public-key", type=Path)
    parser.add_argument("--customer")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--licence-id", default="")
    args = parser.parse_args()
    if args.init:
        if args.public_key is None:
            raise SystemExit("--public-key is required with --init")
        initialise(args.private_key, args.public_key)
        return
    if not args.customer:
        raise SystemExit("--customer is required when issuing a licence")
    print(issue(args.private_key, args.customer, args.days, args.licence_id))


if __name__ == "__main__":
    main()
