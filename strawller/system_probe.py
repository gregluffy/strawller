"""Host system detection: distro fingerprinting, Flatpak, and Snap probing."""

import os
import subprocess

_PKG_MANAGER_MAP = {
    "debian": ("apt", "pkexec apt install -y"),
    "ubuntu": ("apt", "pkexec apt install -y"),
    "linuxmint": ("apt", "pkexec apt install -y"),
    "pop": ("apt", "pkexec apt install -y"),
    "elementary": ("apt", "pkexec apt install -y"),
    "arch": ("pacman", "pkexec pacman -S --noconfirm"),
    "manjaro": ("pacman", "pkexec pacman -S --noconfirm"),
    "endeavouros": ("pacman", "pkexec pacman -S --noconfirm"),
    "garuda": ("pacman", "pkexec pacman -S --noconfirm"),
    "fedora": ("dnf", "pkexec dnf install -y"),
    "rhel": ("dnf", "pkexec dnf install -y"),
    "centos": ("dnf", "pkexec dnf install -y"),
    "rocky": ("dnf", "pkexec dnf install -y"),
    "alma": ("dnf", "pkexec dnf install -y"),
    "opensuse": ("dnf", "pkexec dnf install -y"),
}

_PKG_BINARY = {
    "apt": "/usr/bin/apt",
    "pacman": "/usr/bin/pacman",
    "dnf": "/usr/bin/dnf",
}


def detect_distro(os_release_path: str = "/etc/os-release") -> dict:
    """Parse /etc/os-release and return distro profile."""
    fields = {}
    try:
        with open(os_release_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    fields[key.strip()] = value.strip().strip('"')
    except OSError:
        pass

    distro_id = fields.get("ID", "").lower()
    id_like = fields.get("ID_LIKE", "").lower().split()

    for candidate in [distro_id] + id_like:
        if candidate in _PKG_MANAGER_MAP:
            pkg_manager, install_cmd = _PKG_MANAGER_MAP[candidate]
            return {
                "id": distro_id,
                "id_like": id_like,
                "pretty_name": fields.get("PRETTY_NAME", distro_id),
                "pkg_manager": pkg_manager,
                "install_cmd": install_cmd,
                "pkg_binary": _PKG_BINARY.get(pkg_manager, ""),
            }

    return {
        "id": distro_id,
        "id_like": id_like,
        "pretty_name": fields.get("PRETTY_NAME", "Unknown"),
        "pkg_manager": None,
        "install_cmd": None,
        "pkg_binary": None,
    }


def detect_flatpak() -> bool:
    """Return True if flatpak is installed and the flathub remote is configured."""
    if not os.path.isfile("/usr/bin/flatpak"):
        return False
    try:
        result = subprocess.run(
            ["flatpak", "remotes"],
            capture_output=True, text=True, timeout=5
        )
        return "flathub" in result.stdout.lower()
    except (OSError, subprocess.TimeoutExpired):
        return False


def detect_snap() -> bool:
    """Return True if snapd is present and responsive."""
    snap_bin = "/usr/bin/snap"
    snap_socket = "/var/lib/snapd/snap"
    if os.path.isfile(snap_bin) or os.path.exists(snap_socket):
        try:
            result = subprocess.run(
                ["snap", "version"],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return os.path.isfile(snap_bin)
    return False


def get_system_profile() -> dict:
    """Aggregate distro, flatpak, and snap detection into a single profile dict."""
    profile = detect_distro()
    profile["flatpak"] = detect_flatpak()
    profile["snap"] = detect_snap()
    return profile
