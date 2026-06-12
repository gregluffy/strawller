"""Load and query the apps.json metadata database."""

import json
import os
from typing import Any


def load_apps(path: str) -> dict:
    """Load apps.json from *path* and return the parsed dict."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "categories" not in data:
        raise ValueError(f"apps.json missing 'categories' key: {path}")
    return data


def get_default_path() -> str:
    """Return the bundled data/apps.json path relative to this file."""
    return os.path.join(os.path.dirname(__file__), "..", "data", "apps.json")


def get_categories(data: dict) -> list[dict]:
    """Return a list of category dicts sorted by display_name."""
    cats = []
    for cat_id, cat in data.get("categories", {}).items():
        cats.append({
            "id": cat_id,
            "display_name": cat.get("display_name", cat_id),
            "icon_name": cat.get("icon_name", "applications-other-symbolic"),
        })
    return sorted(cats, key=lambda c: c["display_name"])


def get_apps_for_category(data: dict, category_id: str) -> list[dict]:
    """Return the list of app dicts for a given category id."""
    return data.get("categories", {}).get(category_id, {}).get("apps", [])


def get_all_apps(data: dict) -> list[dict]:
    """Return a flat list of all app dicts across all categories."""
    apps = []
    for cat in data.get("categories", {}).values():
        apps.extend(cat.get("apps", []))
    return apps


def find_app_by_id(data: dict, app_id: str) -> dict | None:
    """Return the app dict matching *app_id*, or None if not found."""
    for app in get_all_apps(data):
        if app.get("id") == app_id:
            return app
    return None
