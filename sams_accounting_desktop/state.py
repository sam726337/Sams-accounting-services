from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re


APP_STATE_DIR = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / "SamsAccountingDesktop"
SETTINGS_FILE = APP_STATE_DIR / "settings.json"


@dataclass
class AppSettings:
    license_verified: bool = False
    user_name: str = ""
    contact: str = ""
    license_key: str = ""
    verified_at: str = ""
    setup_done: bool = False


def load_settings() -> AppSettings:
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AppSettings()
    return AppSettings(**{field: data.get(field, getattr(AppSettings(), field)) for field in AppSettings.__dataclass_fields__})


def save_settings(settings: AppSettings) -> None:
    APP_STATE_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")


def is_license_verified() -> bool:
    return load_settings().license_verified


def verify_license_details(name: str, contact: str, license_key: str) -> tuple[bool, str, AppSettings | None]:
    cleaned_name = " ".join(name.split())
    cleaned_contact = contact.strip()
    cleaned_key = license_key.strip().upper()

    if len(cleaned_name) < 2:
        return False, "Name enter karein."
    if not is_valid_contact(cleaned_contact):
        return False, "Valid email ya 10 digit mobile number enter karein."
    if not is_valid_license_key(cleaned_key):
        return False, "License key SAM- se start honi chahiye. Demo ke liye SAM-DEMO use kar sakte hain."

    settings = load_settings()
    settings.license_verified = True
    settings.user_name = cleaned_name
    settings.contact = cleaned_contact
    settings.license_key = cleaned_key
    settings.verified_at = datetime.now().isoformat(timespec="seconds")
    save_settings(settings)
    return True, "License verified. Dashboard opening.", settings


def start_local_trial(name: str, contact: str) -> tuple[bool, str, AppSettings | None]:
    cleaned_name = " ".join(name.split()) or "sameer mansuri"
    cleaned_contact = contact.strip() or "local"
    settings = load_settings()
    settings.license_verified = True
    settings.user_name = cleaned_name
    settings.contact = cleaned_contact
    settings.license_key = "LOCAL-TRIAL"
    settings.verified_at = datetime.now().isoformat(timespec="seconds")
    save_settings(settings)
    return True, "Local trial activated. Dashboard opening.", settings


def is_valid_contact(value: str) -> bool:
    if "@" in value and "." in value.rsplit("@", 1)[-1]:
        return True
    return len(re.sub(r"\D+", "", value)) >= 10


def is_valid_license_key(value: str) -> bool:
    if value == "SAM-DEMO":
        return True
    return value.startswith("SAM-") and len(value) >= 8
