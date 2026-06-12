"""Persist user settings to ~/.config/strawller/settings.json."""

from __future__ import annotations

import json
import os

_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "strawller")
_SETTINGS_FILE = os.path.join(_CONFIG_DIR, "settings.json")

_DEFAULTS: dict = {
    "source_order": ["flatpak", "native", "snap"],
}


def load_settings() -> dict:
    """Load settings from disk, falling back to defaults for missing keys."""
    settings = dict(_DEFAULTS)
    try:
        with open(_SETTINGS_FILE, encoding="utf-8") as f:
            on_disk = json.load(f)
        settings.update(on_disk)
    except (OSError, json.JSONDecodeError):
        pass
    return settings


def save_settings(settings: dict) -> None:
    """Persist *settings* to disk, creating the config directory if needed."""
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
