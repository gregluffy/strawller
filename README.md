# Strawller

A modern post-installation app for Linux desktops. Browse and batch-install applications from a curated catalogue of **111 apps across 9 categories**, with intelligent multi-source resolution across native package managers (apt / dnf / pacman), Flatpak, and Snap.

Built with **Python 3.10+**, **GTK 4**, and **Libadwaita**.

---

## Features

- **Distro detection** — reads `/etc/os-release` and auto-selects apt, dnf, or pacman
- **Multi-source priority engine** — prefers Flatpak → Native → Snap by default; fully configurable
- **Batch installation** — queues all selections into one transaction per source type
- **Polkit elevation** — uses `pkexec` for privilege separation; the GUI stays unprivileged
- **Live terminal log** — real-time stdout/stderr streamed into the install dialog
- **Export / Import profiles** — save your selections to JSON and restore them on another machine
- **Search & sort** — filter by name/description; sort by Most Common, A–Z, or Star rating
- **Responsive layout** — `Adw.NavigationSplitView` collapses the sidebar on narrow windows

### Categories

| Category | Apps |
|---|---|
| Development & Engineering | VSCode, Neovim, Docker, Postman, GitHub CLI, DBeaver … |
| Web Browsers | Firefox, Brave, Chromium, LibreWolf, Tor Browser … |
| Multimedia & Production | VLC, OBS Studio, GIMP, Blender, Kdenlive, Krita … |
| Productivity & Office | LibreOffice, Obsidian, Thunderbird, Calibre, Joplin … |
| Communication & Chat | Discord, Signal, Telegram, Element, Zoom, Slack … |
| Gaming & Emulation | Steam, Lutris, Heroic, Bottles, RetroArch, Wine … |
| System Tools & Tweaks | Timeshift, GParted, Btop, GNOME Tweaks, Flatseal … |
| Utilities & Security | KeePassXC, Bitwarden, Remmina, Flameshot, qBittorrent … |
| Cloud & File Sync | Syncthing, rclone, Dropbox, MEGA, Restic … |

---

## Requirements

| Dependency | Version |
|---|---|
| Python | 3.10+ |
| PyGObject | ≥ 3.44 |
| GTK 4 | system package |
| Libadwaita | system package |

Install the system libraries:

```bash
# Debian / Ubuntu
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1

# Fedora
sudo dnf install python3-gobject gtk4 libadwaita

# Arch / Manjaro
sudo pacman -S python-gobject gtk4 libadwaita
```

Install the Python binding:

```bash
pip install PyGObject
```

---

## Running the App

```bash
git clone <repo-url>
cd strawinstaller

python strawller.py
```

The app detects your distro and available package sources automatically on startup.

### First-time setup

1. Launch Strawller — the sidebar lists all 9 categories.
2. Click a category to browse its apps.
3. Check the apps you want to install. Each card shows which sources are available; use the dropdown to override the auto-selected source.
4. Click **Install Selected (N)** in the bottom bar.
5. Authenticate when Polkit prompts for your password — the GUI itself never runs as root.
6. Watch live progress in the install dialog. Expand "Show terminal output" for the full log.

### Export & Import profiles

Save your selection to a file to reuse it on another machine:

- **Export Profile** (bottom bar) → saves a `strawller-profile.json` file
- **Import Profile** (bottom bar) → loads a previously exported file and restores all checkboxes

Profile format:

```json
{
  "version": 1,
  "selections": [
    { "app_id": "vscode",  "source_override": "flatpak" },
    { "app_id": "vlc",     "source_override": null }
  ]
}
```

### Changing source priority

Click the **⚙ Preferences** button at the bottom of the sidebar. Use the up/down arrows to reorder Flatpak, Native, and Snap. Click **Save** — the new order takes effect immediately and is persisted to `~/.config/strawller/settings.json`.

---

## Running Tests

The test suite covers the three core logic modules — **no GTK display required**, so tests run on any platform.

```bash
pip install pytest
python -m pytest tests/ -v
```

Expected output:

```
tests/test_data_loader.py::test_load_apps_valid                          PASSED
tests/test_data_loader.py::test_get_categories_sorted_by_display_name    PASSED
tests/test_data_loader.py::test_live_apps_json_loads                     PASSED
...
tests/test_priority_engine.py::test_resolve_flatpak_first_when_all_available  PASSED
tests/test_priority_engine.py::test_build_batches_separates_sources           PASSED
...
tests/test_system_probe.py::test_detect_distro_ubuntu                    PASSED
tests/test_system_probe.py::test_detect_distro_arch                      PASSED
...
```

### What is tested

| Module | Tests |
|---|---|
| `system_probe.py` | `/etc/os-release` parsing for Debian, Arch, Fedora, unknown; Flatpak/Snap detection with mocked binaries and timeouts |
| `priority_engine.py` | Source resolution with all combinations of available sources; fallback chain; manual override; `build_batches` grouping; unresolved tracking |
| `data_loader.py` | JSON loading and validation; category/app querying; live smoke test against `data/apps.json` |

---

## Project Structure

```
strawinstaller/
├── strawller.py                  # Entry point: python strawller.py
├── strawller/
│   ├── main.py                   # Adw.Application subclass
│   ├── window.py                 # Main window (NavigationSplitView)
│   ├── system_probe.py           # Distro + Flatpak/Snap detection
│   ├── priority_engine.py        # Multi-source resolution & batch builder
│   ├── installer.py              # Threaded install runner (pkexec)
│   ├── data_loader.py            # apps.json loader & query helpers
│   ├── preferences_window.py     # Source priority preferences
│   ├── settings.py               # ~/.config/strawller/settings.json
│   ├── profile_io.py             # Export/import ~/.local/share/strawller/
│   └── widgets/
│       ├── app_card.py           # Per-app card widget
│       └── install_dialog.py     # Progress dialog with live log
├── data/
│   └── apps.json                 # 111-app catalogue
├── tests/
│   ├── test_system_probe.py
│   ├── test_priority_engine.py
│   └── test_data_loader.py
└── requirements.txt
```

---

## Adding More Apps

Open `data/apps.json` and add an entry to the relevant category's `apps` array:

```json
{
  "id": "unique-id",
  "name": "Display Name",
  "description": "One-line description.",
  "stars": 4.5,
  "is_common": false,
  "sources": {
    "apt":     "package-name",
    "dnf":     "package-name",
    "pacman":  "package-name",
    "flatpak": "com.example.App",
    "snap":    "package-name"
  }
}
```

Only include the `sources` keys that actually exist — omit any that don't have a package for that manager. The priority engine skips unavailable sources automatically.
