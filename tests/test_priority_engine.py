"""Tests for priority_engine.py."""

import pytest

from strawller.priority_engine import PriorityEngine, DEFAULT_ORDER

# Sample app with all sources
_FULL_APP = {
    "id": "vlc",
    "name": "VLC",
    "sources": {
        "apt": "vlc",
        "pacman": "vlc",
        "dnf": "vlc",
        "flatpak": "org.videolan.VLC",
        "snap": "vlc",
    },
}

# App with only native apt
_APT_ONLY_APP = {
    "id": "git",
    "name": "Git",
    "sources": {"apt": "git", "dnf": "git", "pacman": "git"},
}

# App with only flatpak
_FLATPAK_ONLY_APP = {
    "id": "flatseal",
    "name": "Flatseal",
    "sources": {"flatpak": "com.github.tchx84.Flatseal"},
}

_PROFILE_ALL = {
    "pkg_manager": "apt",
    "flatpak": True,
    "snap": True,
}

_PROFILE_APT_ONLY = {
    "pkg_manager": "apt",
    "flatpak": False,
    "snap": False,
}

_PROFILE_NO_NATIVE = {
    "pkg_manager": None,
    "flatpak": True,
    "snap": True,
}


# ---------------------------------------------------------------------------
# resolve()
# ---------------------------------------------------------------------------

def test_resolve_flatpak_first_when_all_available():
    engine = PriorityEngine(_PROFILE_ALL, ["flatpak", "native", "snap"])
    source, pkg = engine.resolve(_FULL_APP)
    assert source == "flatpak"
    assert pkg == "org.videolan.VLC"


def test_resolve_native_first():
    engine = PriorityEngine(_PROFILE_ALL, ["native", "flatpak", "snap"])
    source, pkg = engine.resolve(_FULL_APP)
    assert source == "native"
    assert pkg == "vlc"


def test_resolve_snap_first():
    engine = PriorityEngine(_PROFILE_ALL, ["snap", "native", "flatpak"])
    source, pkg = engine.resolve(_FULL_APP)
    assert source == "snap"
    assert pkg == "vlc"


def test_resolve_fallback_to_next_when_top_unavailable():
    # Flatpak not available, should fall through to native
    engine = PriorityEngine(_PROFILE_APT_ONLY, ["flatpak", "native", "snap"])
    source, pkg = engine.resolve(_FULL_APP)
    assert source == "native"
    assert pkg == "vlc"


def test_resolve_returns_none_when_nothing_available():
    engine = PriorityEngine(_PROFILE_APT_ONLY, ["flatpak", "native", "snap"])
    source, pkg = engine.resolve(_FLATPAK_ONLY_APP)
    assert source is None
    assert pkg is None


def test_resolve_override_forces_source():
    engine = PriorityEngine(_PROFILE_ALL, ["flatpak", "native", "snap"])
    source, pkg = engine.resolve(_FULL_APP, override="snap")
    assert source == "snap"
    assert pkg == "vlc"


def test_resolve_override_unavailable_returns_none():
    engine = PriorityEngine(_PROFILE_APT_ONLY, ["native"])
    source, pkg = engine.resolve(_FULL_APP, override="flatpak")
    assert source is None


def test_resolve_pacman_profile():
    profile = {"pkg_manager": "pacman", "flatpak": False, "snap": False}
    engine = PriorityEngine(profile, ["native"])
    source, pkg = engine.resolve(_FULL_APP)
    assert source == "native"
    assert pkg == "vlc"


# ---------------------------------------------------------------------------
# available_sources()
# ---------------------------------------------------------------------------

def test_available_sources_all():
    engine = PriorityEngine(_PROFILE_ALL)
    sources = engine.available_sources(_FULL_APP)
    types = [s for s, _ in sources]
    assert "flatpak" in types
    assert "native" in types
    assert "snap" in types


def test_available_sources_none():
    engine = PriorityEngine(_PROFILE_APT_ONLY)
    sources = engine.available_sources(_FLATPAK_ONLY_APP)
    assert sources == []


def test_available_sources_flatpak_only_app_with_full_profile():
    engine = PriorityEngine(_PROFILE_ALL)
    sources = engine.available_sources(_FLATPAK_ONLY_APP)
    assert len(sources) == 1
    assert sources[0][0] == "flatpak"


# ---------------------------------------------------------------------------
# build_batches()
# ---------------------------------------------------------------------------

def test_build_batches_separates_sources():
    engine = PriorityEngine(_PROFILE_ALL, ["native", "flatpak", "snap"])
    selections = [
        (_APT_ONLY_APP, None),   # → native
        (_FLATPAK_ONLY_APP, None),  # → flatpak
    ]
    batches = engine.build_batches(selections)
    assert "git" in batches["native"]["packages"]
    assert "com.github.tchx84.Flatseal" in batches["flatpak"]["packages"]
    assert batches["snap"]["packages"] == []


def test_build_batches_unresolved_logged():
    engine = PriorityEngine(_PROFILE_APT_ONLY, ["native"])
    selections = [(_FLATPAK_ONLY_APP, None)]
    batches = engine.build_batches(selections)
    assert "flatseal" in batches["unresolved"]


def test_build_batches_respects_override():
    engine = PriorityEngine(_PROFILE_ALL, ["flatpak", "native", "snap"])
    selections = [(_FULL_APP, "snap")]
    batches = engine.build_batches(selections)
    assert "vlc" in batches["snap"]["packages"]
    assert batches["flatpak"]["packages"] == []


def test_build_batches_empty():
    engine = PriorityEngine(_PROFILE_ALL)
    batches = engine.build_batches([])
    assert batches["native"]["packages"] == []
    assert batches["flatpak"]["packages"] == []
    assert batches["snap"]["packages"] == []
    assert batches["unresolved"] == []


# ---------------------------------------------------------------------------
# order property
# ---------------------------------------------------------------------------

def test_order_property_roundtrip():
    engine = PriorityEngine(_PROFILE_ALL)
    engine.order = ["snap", "native", "flatpak"]
    assert engine.order == ["snap", "native", "flatpak"]
