"""Tests for data_loader.py."""

import json
import os
import tempfile

import pytest

from strawller.data_loader import (
    load_apps,
    get_categories,
    get_apps_for_category,
    get_all_apps,
    find_app_by_id,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MINI_DATA = {
    "categories": {
        "browsers": {
            "display_name": "Web Browsers",
            "icon_name": "web-browser-symbolic",
            "apps": [
                {
                    "id": "firefox",
                    "name": "Firefox",
                    "description": "Fast browser.",
                    "stars": 4.6,
                    "is_common": True,
                    "sources": {"apt": "firefox", "flatpak": "org.mozilla.firefox"},
                },
                {
                    "id": "brave",
                    "name": "Brave",
                    "description": "Privacy browser.",
                    "stars": 4.5,
                    "is_common": True,
                    "sources": {"flatpak": "com.brave.Browser"},
                },
            ],
        },
        "development": {
            "display_name": "Development",
            "icon_name": "developer-mode-symbolic",
            "apps": [
                {
                    "id": "vscode",
                    "name": "Visual Studio Code",
                    "description": "Code editor.",
                    "stars": 4.7,
                    "is_common": True,
                    "sources": {"apt": "code", "flatpak": "com.visualstudio.code"},
                }
            ],
        },
    }
}


def _write_json(data: dict) -> str:
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(data, f)
    f.close()
    return f.name


# ---------------------------------------------------------------------------
# load_apps
# ---------------------------------------------------------------------------

def test_load_apps_valid():
    path = _write_json(_MINI_DATA)
    try:
        data = load_apps(path)
        assert "categories" in data
        assert "browsers" in data["categories"]
    finally:
        os.unlink(path)


def test_load_apps_missing_categories_key():
    path = _write_json({"apps": []})
    try:
        with pytest.raises(ValueError, match="missing 'categories'"):
            load_apps(path)
    finally:
        os.unlink(path)


def test_load_apps_file_not_found():
    with pytest.raises(OSError):
        load_apps("/nonexistent/apps.json")


# ---------------------------------------------------------------------------
# get_categories
# ---------------------------------------------------------------------------

def test_get_categories_sorted_by_display_name():
    cats = get_categories(_MINI_DATA)
    names = [c["display_name"] for c in cats]
    assert names == sorted(names)


def test_get_categories_includes_id_and_icon():
    cats = get_categories(_MINI_DATA)
    ids = {c["id"] for c in cats}
    assert "browsers" in ids
    assert "development" in ids
    for cat in cats:
        assert "icon_name" in cat


# ---------------------------------------------------------------------------
# get_apps_for_category
# ---------------------------------------------------------------------------

def test_get_apps_for_category_returns_apps():
    apps = get_apps_for_category(_MINI_DATA, "browsers")
    assert len(apps) == 2
    assert apps[0]["id"] in ("firefox", "brave")


def test_get_apps_for_category_unknown_returns_empty():
    apps = get_apps_for_category(_MINI_DATA, "nonexistent")
    assert apps == []


# ---------------------------------------------------------------------------
# get_all_apps
# ---------------------------------------------------------------------------

def test_get_all_apps_flattens_categories():
    apps = get_all_apps(_MINI_DATA)
    ids = {a["id"] for a in apps}
    assert ids == {"firefox", "brave", "vscode"}


# ---------------------------------------------------------------------------
# find_app_by_id
# ---------------------------------------------------------------------------

def test_find_app_by_id_found():
    app = find_app_by_id(_MINI_DATA, "firefox")
    assert app is not None
    assert app["name"] == "Firefox"


def test_find_app_by_id_not_found():
    app = find_app_by_id(_MINI_DATA, "nonexistent")
    assert app is None


# ---------------------------------------------------------------------------
# Live apps.json smoke test
# ---------------------------------------------------------------------------

def test_live_apps_json_loads():
    """Ensure the real apps.json parses without error."""
    from strawller.data_loader import get_default_path
    path = get_default_path()
    data = load_apps(path)
    cats = get_categories(data)
    assert len(cats) >= 9
    all_apps = get_all_apps(data)
    assert len(all_apps) >= 100
    # Every app must have id, name, sources
    for app in all_apps:
        assert "id" in app, f"Missing id: {app}"
        assert "name" in app, f"Missing name: {app}"
        assert "sources" in app, f"Missing sources: {app}"
