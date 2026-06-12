"""Export and import user selection profiles."""

from __future__ import annotations

import json
import os

_PROFILE_VERSION = 1
_DEFAULT_PROFILE_DIR = os.path.join(
    os.path.expanduser("~"), ".local", "share", "strawller"
)


def export_profile(selections: dict[str, str | None], path: str) -> None:
    """Write *selections* (app_id -> source_override) to *path* as JSON."""
    payload = {
        "version": _PROFILE_VERSION,
        "selections": [
            {"app_id": app_id, "source_override": override}
            for app_id, override in selections.items()
        ],
    }
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def import_profile(path: str) -> dict[str, str | None]:
    """Load a profile JSON and return a selections dict (app_id -> override)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if data.get("version") != _PROFILE_VERSION:
        raise ValueError(f"Unsupported profile version: {data.get('version')}")

    selections: dict[str, str | None] = {}
    for entry in data.get("selections", []):
        app_id = entry.get("app_id")
        if app_id:
            selections[app_id] = entry.get("source_override")
    return selections
