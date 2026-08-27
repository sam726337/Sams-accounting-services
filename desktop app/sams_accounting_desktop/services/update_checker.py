from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
import urllib.error
import urllib.request

from sams_accounting_desktop.config import APP_VERSION, UPDATE_CHECK_TIMEOUT_SECONDS, UPDATE_MANIFEST_URL


@dataclass(frozen=True)
class UpdateInfo:
    latest_version: str
    download_url: str
    release_notes: str = ""
    mandatory: bool = False
    source_url: str = ""


@dataclass(frozen=True)
class UpdateCheckResult:
    current_version: str
    update_available: bool
    info: UpdateInfo | None = None
    error: str = ""


def update_manifest_url() -> str:
    return os.environ.get("SAMS_ACCOUNTING_UPDATE_URL", UPDATE_MANIFEST_URL).strip() or UPDATE_MANIFEST_URL


def check_for_update(current_version: str = APP_VERSION) -> UpdateCheckResult:
    url = update_manifest_url()
    try:
        info = fetch_update_manifest(url)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        return UpdateCheckResult(current_version=current_version, update_available=False, error=str(exc))

    update_available = compare_versions(info.latest_version, current_version) > 0
    return UpdateCheckResult(
        current_version=current_version,
        update_available=update_available,
        info=info,
    )


def fetch_update_manifest(url: str) -> UpdateInfo:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "SamsAccountingDesktop/1.0",
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=UPDATE_CHECK_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8", errors="replace"))

    if payload.get("ok") is False:
        raise ValueError("Update manifest returned ok=false.")

    latest_version = str(payload.get("latest_version") or "").strip()
    download_url = str(payload.get("download_url") or "").strip()
    if not latest_version or not download_url:
        raise ValueError("Update manifest missing latest_version or download_url.")

    return UpdateInfo(
        latest_version=latest_version,
        download_url=download_url,
        release_notes=str(payload.get("release_notes") or "").strip(),
        mandatory=bool(payload.get("mandatory", False)),
        source_url=url,
    )


def compare_versions(latest_version: str, current_version: str) -> int:
    latest = version_tuple(latest_version)
    current = version_tuple(current_version)
    max_len = max(len(latest), len(current), 1)
    latest += (0,) * (max_len - len(latest))
    current += (0,) * (max_len - len(current))
    if latest > current:
        return 1
    if latest < current:
        return -1
    return 0


def version_tuple(value: str) -> tuple[int, ...]:
    cleaned = str(value or "").strip().lower().removeprefix("v")
    numbers = re.findall(r"\d+", cleaned)
    return tuple(int(number) for number in numbers) if numbers else (0,)
