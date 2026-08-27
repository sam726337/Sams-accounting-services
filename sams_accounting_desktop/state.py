from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import re

from sams_accounting_desktop.config import TERMS_VERSION, TRIAL_DAYS
from sams_accounting_desktop.license_keys import validate_signed_license


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
    licence_id: str = ""
    licence_expires: str = ""
    trial_expires: str = ""
    terms_accepted: bool = False
    privacy_accepted: bool = False
    consent_version: str = ""
    consent_accepted_at: str = ""


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
    settings = load_settings()
    if not settings.license_verified:
        return False
    if not settings.terms_accepted or not settings.privacy_accepted:
        return False
    if settings.consent_version != TERMS_VERSION:
        return False
    if settings.license_key == "LOCAL-TRIAL":
        try:
            return date.fromisoformat(settings.trial_expires) >= date.today()
        except ValueError:
            return False
    ok, _message, _claims = validate_signed_license(settings.license_key)
    return ok


def verify_license_details(
    name: str,
    contact: str,
    license_key: str,
    *,
    terms_accepted: bool = False,
    privacy_accepted: bool = False,
) -> tuple[bool, str, AppSettings | None]:
    cleaned_name = " ".join(name.split())
    cleaned_contact = contact.strip()
    cleaned_key = license_key.strip()

    if len(cleaned_name) < 2:
        return False, "Enter your name.", None
    if not is_valid_contact(cleaned_contact):
        return False, "Enter a valid email address or 10-digit mobile number.", None
    if not terms_accepted or not privacy_accepted:
        return False, "Accept both the Terms of Use and Privacy Policy to continue.", None
    licence_ok, licence_message, claims = validate_signed_license(cleaned_key)
    if not licence_ok or claims is None:
        return False, licence_message

    settings = load_settings()
    settings.license_verified = True
    settings.user_name = cleaned_name
    settings.contact = cleaned_contact
    settings.license_key = cleaned_key
    settings.licence_id = claims.licence_id
    settings.licence_expires = claims.expires.isoformat()
    settings.trial_expires = ""
    settings.verified_at = datetime.now().isoformat(timespec="seconds")
    record_consent(settings, terms_accepted=terms_accepted, privacy_accepted=privacy_accepted)
    save_settings(settings)
    return True, f"{licence_message} Opening dashboard.", settings


def start_local_trial(
    name: str,
    contact: str,
    *,
    terms_accepted: bool = False,
    privacy_accepted: bool = False,
) -> tuple[bool, str, AppSettings | None]:
    cleaned_name = " ".join(name.split()) or "Local Trial User"
    cleaned_contact = contact.strip() or "local"
    if not terms_accepted or not privacy_accepted:
        return False, "Accept both the Terms of Use and Privacy Policy to start a trial.", None
    settings = load_settings()
    settings.license_verified = True
    settings.user_name = cleaned_name
    settings.contact = cleaned_contact
    settings.license_key = "LOCAL-TRIAL"
    settings.licence_id = "LOCAL-TRIAL"
    settings.licence_expires = ""
    settings.trial_expires = (date.today() + timedelta(days=TRIAL_DAYS)).isoformat()
    settings.verified_at = datetime.now().isoformat(timespec="seconds")
    record_consent(settings, terms_accepted=terms_accepted, privacy_accepted=privacy_accepted)
    save_settings(settings)
    return True, f"{TRIAL_DAYS}-day local trial activated. Opening dashboard.", settings


def record_consent(settings: AppSettings, *, terms_accepted: bool, privacy_accepted: bool) -> None:
    settings.terms_accepted = bool(terms_accepted)
    settings.privacy_accepted = bool(privacy_accepted)
    settings.consent_version = TERMS_VERSION
    settings.consent_accepted_at = datetime.now().isoformat(timespec="seconds")


def is_valid_contact(value: str) -> bool:
    if "@" in value and "." in value.rsplit("@", 1)[-1]:
        return True
    return len(re.sub(r"\D+", "", value)) >= 10


def is_valid_license_key(value: str) -> bool:
    ok, _message, _claims = validate_signed_license(value)
    return ok
