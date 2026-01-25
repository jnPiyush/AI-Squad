import json
import os
import sys
import urllib.request
from importlib import metadata

PACKAGE_NAME = "github-copilot-sdk"
PYPI_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"


def _parse_version(value: str) -> tuple:
    parts = []
    for chunk in value.replace("-", ".").split("."):
        if chunk.isdigit():
            parts.append(int(chunk))
        else:
            digits = "".join(ch for ch in chunk if ch.isdigit())
            parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _get_installed_version() -> str:
    return metadata.version(PACKAGE_NAME)


def _get_latest_version() -> str:
    with urllib.request.urlopen(PYPI_URL, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload["info"]["version"]


def main() -> int:
    if os.getenv("AI_SQUAD_SKIP_SDK_VERSION_CHECK"):
        return 0

    try:
        installed = _get_installed_version()
    except metadata.PackageNotFoundError:
        print(f"FAIL {PACKAGE_NAME} is not installed.")
        return 1

    try:
        latest = _get_latest_version()
    except Exception as exc:
        print(f"WARN Unable to check latest {PACKAGE_NAME} version: {exc}")
        return 0

    if _parse_version(installed) < _parse_version(latest):
        print(
            f"FAIL {PACKAGE_NAME} is outdated. Installed: {installed}, Latest: {latest}"
        )
        print("TIP Run: pip install --upgrade github-copilot-sdk")
        return 1

    print(f"OK {PACKAGE_NAME} is up to date ({installed}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
