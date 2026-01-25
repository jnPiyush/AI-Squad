"""Copilot SDK compatibility checks and auto-fix."""
from __future__ import annotations

import json
import importlib.util
import os
import subprocess
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass
from importlib import metadata
from typing import Optional, Tuple

PACKAGE_NAME = "github-copilot-sdk"
PYPI_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
MIN_VERSION = "0.1.16"
KNOWN_GOOD_VERSION = "0.1.16"


@dataclass
class SdkCompatResult:
    ok: bool
    installed: Optional[str]
    latest: Optional[str]
    action: Optional[str]
    message: str


def _parse_version(value: str) -> Tuple[int, ...]:
    parts = []
    for chunk in value.replace("-", ".").split("."):
        if chunk.isdigit():
            parts.append(int(chunk))
        else:
            digits = "".join(ch for ch in chunk if ch.isdigit())
            parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _get_installed_version() -> Optional[str]:
    try:
        return metadata.version(PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        return None


def _get_latest_version() -> Optional[str]:
    try:
        with urllib.request.urlopen(PYPI_URL, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload.get("info", {}).get("version")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None


def _is_sdk_compatible() -> bool:
    return bool(importlib.util.find_spec("copilot") or importlib.util.find_spec("github_copilot_sdk"))


def _pip_install(spec: str) -> bool:
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", spec],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def ensure_copilot_sdk_compat(
    *,
    auto_fix: bool = True,
    allow_network: bool = True,
) -> SdkCompatResult:
    if os.getenv("AI_SQUAD_SKIP_SDK_COMPAT"):
        return SdkCompatResult(
            ok=True,
            installed=_get_installed_version(),
            latest=None,
            action=None,
            message="Compatibility check skipped",
        )

    installed = _get_installed_version()
    latest = _get_latest_version() if allow_network else None

    if not installed:
        if not auto_fix:
            return SdkCompatResult(
                ok=False,
                installed=None,
                latest=latest,
                action=None,
                message="Copilot SDK not installed",
            )
        target = latest or KNOWN_GOOD_VERSION
        action = f"install {PACKAGE_NAME}=={target}"
        if _pip_install(f"{PACKAGE_NAME}=={target}") and _is_sdk_compatible():
            return SdkCompatResult(True, target, latest, action, "Installed Copilot SDK")
        return SdkCompatResult(False, None, latest, action, "Failed to install Copilot SDK")

    if _parse_version(installed) < _parse_version(MIN_VERSION):
        if not auto_fix:
            return SdkCompatResult(
                ok=False,
                installed=installed,
                latest=latest,
                action=None,
                message=f"Copilot SDK below minimum {MIN_VERSION}",
            )
        target = latest or MIN_VERSION
        action = f"upgrade {PACKAGE_NAME}=={target}"
        if _pip_install(f"{PACKAGE_NAME}=={target}") and _is_sdk_compatible():
            return SdkCompatResult(True, target, latest, action, "Upgraded Copilot SDK")
        return SdkCompatResult(False, installed, latest, action, "Failed to upgrade Copilot SDK")

    if not _is_sdk_compatible():
        if not auto_fix:
            return SdkCompatResult(
                ok=False,
                installed=installed,
                latest=latest,
                action=None,
                message="Copilot SDK API incompatibility detected",
            )
        action = f"install {PACKAGE_NAME}=={KNOWN_GOOD_VERSION}"
        if _pip_install(f"{PACKAGE_NAME}=={KNOWN_GOOD_VERSION}") and _is_sdk_compatible():
            return SdkCompatResult(True, KNOWN_GOOD_VERSION, latest, action, "Pinned compatible Copilot SDK")
        return SdkCompatResult(False, installed, latest, action, "Failed to pin compatible Copilot SDK")

    if latest and _parse_version(installed) < _parse_version(latest):
        if auto_fix:
            action = f"upgrade {PACKAGE_NAME}=={latest}"
            if _pip_install(f"{PACKAGE_NAME}=={latest}") and _is_sdk_compatible():
                return SdkCompatResult(True, latest, latest, action, "Upgraded Copilot SDK")
            # fallback to known good
            action = f"install {PACKAGE_NAME}=={KNOWN_GOOD_VERSION}"
            if _pip_install(f"{PACKAGE_NAME}=={KNOWN_GOOD_VERSION}") and _is_sdk_compatible():
                return SdkCompatResult(True, KNOWN_GOOD_VERSION, latest, action, "Pinned compatible Copilot SDK")
            return SdkCompatResult(
                True,
                installed,
                latest,
                action,
                "Copilot SDK is usable but could not be upgraded",
            )

    return SdkCompatResult(True, installed, latest, None, "Copilot SDK is compatible")
