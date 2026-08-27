from __future__ import annotations

from datetime import date
import os
from pathlib import Path
import tempfile


qa_state = Path(tempfile.gettempdir()) / "sams-accounting-hardening-qa-20260827"
qa_state.mkdir(parents=True, exist_ok=True)
os.environ["APPDATA"] = str(qa_state)
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from sams_accounting_desktop.config import APP_VERSION, PRIVACY_URL, TERMS_URL, TERMS_VERSION
from sams_accounting_desktop.legal import PRIVACY_POLICY, TERMS_OF_USE
from sams_accounting_desktop.license_keys import validate_signed_license
from sams_accounting_desktop.state import (
    SETTINGS_FILE,
    is_license_verified,
    load_settings,
    start_local_trial,
    verify_license_details,
)
from sams_accounting_desktop.ui.startup import LicenseWindow
from tools.generate_license_key import issue


PRIVATE_KEY = Path(
    r"C:\Users\Sameer Mansuri\Desktop\Sams accounting\.safety_backups\license-private-20260827\ed25519-private.pem"
)
checks: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: object = "") -> None:
    checks.append((name, bool(passed), str(detail)))
    print(f"{'PASS' if passed else 'FAIL'} | {name} | {detail}")


token = issue(PRIVATE_KEY, "Launch QA", 30, "QA-LAUNCH-20260827")
valid, message, claims = validate_signed_license(token)
check("signed licence accepted", valid and claims is not None, message)

tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
check("tampered licence rejected", not validate_signed_license(tampered)[0])

blocked, _, _ = verify_license_details("Launch QA", "qa@example.com", token)
check("licence blocked without consent", not blocked)

verified, message, settings = verify_license_details(
    "Launch QA",
    "qa@example.com",
    token,
    terms_accepted=True,
    privacy_accepted=True,
)
check("licence accepted with consent", verified, message)
check("persisted licence verifies", is_license_verified())
saved = load_settings()
check(
    "versioned consent persisted",
    saved.terms_accepted
    and saved.privacy_accepted
    and saved.consent_version == TERMS_VERSION
    and bool(saved.consent_accepted_at),
    saved.consent_accepted_at,
)

trial_ok, trial_message, trial = start_local_trial(
    "Trial QA", "trial@example.com", terms_accepted=True, privacy_accepted=True
)
check(
    "14-day trial activates",
    trial_ok and trial is not None and date.fromisoformat(trial.trial_expires) > date.today(),
    trial_message,
)

app = QApplication.instance() or QApplication([])
window = LicenseWindow()
check("two consent checkboxes", len(window.findChildren(type(window.terms_checkbox))) == 2)
check("actions initially disabled", not window.verify_button.isEnabled() and not window.trial_button.isEnabled())
window.terms_checkbox.setChecked(True)
check("one consent remains blocked", not window.verify_button.isEnabled() and not window.trial_button.isEnabled())
window.privacy_checkbox.setChecked(True)
check("both consents enable actions", window.verify_button.isEnabled() and window.trial_button.isEnabled())
check("legal documents substantive", len(TERMS_OF_USE) > 2000 and len(PRIVACY_POLICY) > 2000)
check("production policy URLs", TERMS_URL.startswith("https://") and PRIVACY_URL.startswith("https://"))
check("settings written to isolated profile", SETTINGS_FILE.is_file(), SETTINGS_FILE)
check("release version", APP_VERSION == "v1.0.3", APP_VERSION)
window.close()

passed = sum(ok for _, ok, _ in checks)
failed = len(checks) - passed
print(f"SUMMARY | passed={passed} failed={failed} total={len(checks)}")
raise SystemExit(1 if failed else 0)
