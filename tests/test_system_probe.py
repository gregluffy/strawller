"""Tests for system_probe.py — no GTK required."""

import os
import subprocess
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from strawller.system_probe import detect_distro, detect_flatpak, detect_snap, get_system_profile


# ---------------------------------------------------------------------------
# detect_distro
# ---------------------------------------------------------------------------

def _write_os_release(content: str) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
    f.write(content)
    f.close()
    return f.name


def test_detect_distro_ubuntu():
    path = _write_os_release('ID=ubuntu\nID_LIKE="debian"\nPRETTY_NAME="Ubuntu 24.04"\n')
    try:
        result = detect_distro(path)
        assert result["pkg_manager"] == "apt"
        assert "apt install" in result["install_cmd"]
        assert result["pretty_name"] == "Ubuntu 24.04"
    finally:
        os.unlink(path)


def test_detect_distro_debian_via_id_like():
    path = _write_os_release('ID=linuxmint\nID_LIKE="ubuntu debian"\nPRETTY_NAME="Linux Mint 22"\n')
    try:
        result = detect_distro(path)
        assert result["pkg_manager"] == "apt"
    finally:
        os.unlink(path)


def test_detect_distro_arch():
    path = _write_os_release('ID=arch\nPRETTY_NAME="Arch Linux"\n')
    try:
        result = detect_distro(path)
        assert result["pkg_manager"] == "pacman"
        assert "pacman" in result["install_cmd"]
    finally:
        os.unlink(path)


def test_detect_distro_manjaro():
    path = _write_os_release('ID=manjaro\nID_LIKE=arch\nPRETTY_NAME="Manjaro Linux"\n')
    try:
        result = detect_distro(path)
        assert result["pkg_manager"] == "pacman"
    finally:
        os.unlink(path)


def test_detect_distro_fedora():
    path = _write_os_release('ID=fedora\nPRETTY_NAME="Fedora Linux 40"\n')
    try:
        result = detect_distro(path)
        assert result["pkg_manager"] == "dnf"
        assert "dnf install" in result["install_cmd"]
    finally:
        os.unlink(path)


def test_detect_distro_unknown():
    path = _write_os_release('ID=gentoo\nPRETTY_NAME="Gentoo"\n')
    try:
        result = detect_distro(path)
        assert result["pkg_manager"] is None
        assert result["install_cmd"] is None
    finally:
        os.unlink(path)


def test_detect_distro_missing_file():
    result = detect_distro("/nonexistent/os-release")
    assert result["pkg_manager"] is None


# ---------------------------------------------------------------------------
# detect_flatpak
# ---------------------------------------------------------------------------

def test_detect_flatpak_present_with_flathub():
    with (
        patch("os.path.isfile", return_value=True),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(stdout="flathub\n", returncode=0)
        assert detect_flatpak() is True


def test_detect_flatpak_no_binary():
    with patch("os.path.isfile", return_value=False):
        assert detect_flatpak() is False


def test_detect_flatpak_no_flathub_remote():
    with (
        patch("os.path.isfile", return_value=True),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(stdout="fedora\n", returncode=0)
        assert detect_flatpak() is False


def test_detect_flatpak_timeout():
    with (
        patch("os.path.isfile", return_value=True),
        patch("subprocess.run", side_effect=subprocess.TimeoutExpired("flatpak", 5)),
    ):
        assert detect_flatpak() is False


# ---------------------------------------------------------------------------
# detect_snap
# ---------------------------------------------------------------------------

def test_detect_snap_present():
    with (
        patch("os.path.isfile", return_value=True),
        patch("os.path.exists", return_value=True),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        assert detect_snap() is True


def test_detect_snap_absent():
    with (
        patch("os.path.isfile", return_value=False),
        patch("os.path.exists", return_value=False),
    ):
        assert detect_snap() is False


# ---------------------------------------------------------------------------
# get_system_profile
# ---------------------------------------------------------------------------

def test_get_system_profile_keys():
    with (
        patch("strawller.system_probe.detect_distro", return_value={"id": "ubuntu", "pkg_manager": "apt", "install_cmd": "pkexec apt install -y", "pkg_binary": "/usr/bin/apt", "id_like": [], "pretty_name": "Ubuntu"}),
        patch("strawller.system_probe.detect_flatpak", return_value=True),
        patch("strawller.system_probe.detect_snap", return_value=False),
    ):
        profile = get_system_profile()
        assert profile["pkg_manager"] == "apt"
        assert profile["flatpak"] is True
        assert profile["snap"] is False
