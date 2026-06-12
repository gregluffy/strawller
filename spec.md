# Application name Strawstaller

# Technical Specification: Strawstaller Universal Linux Suite
## Architecture & Design Spec for PyGObject (GTK 4 / Libadwaita)

---

## 1. Executive Summary & Vision
**Strawstaller** is an advanced post-installation application engineered for modern Linux desktop environments. By harnessing the power of **PyGObject (GTK 4)** and **Libadwaita**, Strawstaller delivers a high-performance, visually adaptive, and unified software delivery platform. 

The core challenge in modern Linux ecosystems is package management fragmentation (Native Repositories, Flatpaks, and Snaps). Strawstaller simplifies this landscape by providing a centralized database, abstracting package names across distributions, and introducing an intelligent multi-source prioritization engine.

---

## 2. Technical Stack Foundation
To guarantee tight integration with standard Linux desktop workflows, Strawstaller is built exclusively on native system components:

* **Runtime Environment:** Python 3.10+ (Clean syntax, robust built-in JSON, and subprocess modules).
* **UI Toolkit:** **GTK 4** via PyGObject bindings.
* **Design Framework:** **Libadwaita** (`Adw.Application`, `Adw.NavigationSplitView`, `Adw.PreferencesWindow`) ensuring modern UI paradigms, responsive design layouts, and instant synchronization with system dark/light modes.
* **Security Elevation:** **Polkit (`pkexec`)** integration to maintain a secure privilege boundaries (the graphical interface runs completely under user privileges, while elevated permissions are called atomatically via explicit transaction-based tokens).

---

## 3. Host System Intelligence
Strawstaller does not guess system environments; it utilizes deterministic discovery routines.

### Distro Fingerprinting
The application reads `/etc/os-release` parsing the `ID` and `ID_LIKE` fields to classify the system into distinct operational profiles:

| Target ID Family | Detected Binary | Installation Invocation String |
| :--- | :--- | :--- |
| **debian / ubuntu** | `/usr/bin/apt` | `pkexec apt install -y` |
| **arch / manjaro** | `/usr/bin/pacman` | `pkexec pacman -S --noconfirm` |
| **fedora / rhel** | `/usr/bin/dnf` | `pkexec dnf install -y` |

### Environment Probing
Prior to offering universal deployment methods, background checks verify if the universal packaging subsystem daemons or runtimes are active:
* **Flatpak:** Checks for `/usr/bin/flatpak` and verifies the presence of the `flathub` remote.
* **Snap:** Checks for `/usr/bin/snap` or `/var/lib/snapd/snap` sockets.

---

## 4. Multi-Source Priority Engine
When a user selects an application that exists across multiple packaging standards (e.g., VLC Media Player available on Apt, Flathub, and Snapcraft), Strawstaller executes a hierarchical resolution routine based on user-defined weights.

### Conflict Resolution Matrix
The user sets a global preference order or individual exceptions (e.g., `1. Flatpak`, `2. System Native`, `3. Snap`). 


```

```text
File created: Strawstaller_app_spec.md


```

User Selects App (e.g., VLC)
│
▼
Check Priority #1 (Flatpak) ──[Exists?]──► YES ──► Queue for Flatpak Install
│
NO
▼
Check Priority #2 (System)  ──[Exists?]──► YES ──► Queue for Native Package Manager
│
NO
▼
Check Priority #3 (Snap)    ──[Exists?]──► YES ──► Queue for Snap Install
│
NO
▼
Fallback / Flag Error ◄─────────────────────────── No Source Found/Enabled

```

### Transaction Processing
Instead of executing sequential system calls for each chosen application, Strawstaller parses selections into separate transactional batch structures:
* **Native Queue:** Combined into one string: `pkexec apt install -y git vim curl`
* **Flatpak Queue:** Executed sequentially or as a multi-argument string: `flatpak install flathub -y org.videolan.VLC com.visualstudio.code`
* **Snap Queue:** Managed through background concurrent snap directives.

---

## 5. UI/UX Architecture & Layout Spec

Following the GNOME Human Interface Guidelines (HIG), Strawstaller splits the application frame dynamically based on window viewport space.

### Interface Layout Blueprint
1.  **Sidebar (`Adw.NavigationSplitView`):**
    * **Header Bar:** Includes a dynamic search bar tracking system definitions.
    * **Category Navigation List:** Grouped items utilizing `Gtk.ListBox` with selection indicators.
    * **Global Preferences Button:** Launches an inline modal allowing real-time adjustments of packaging tiers.
2.  **Main Content Panel:**
    * **Dynamic Banner:** Shows current distro logo, architecture information, and packaging status flags.
    * **View Settings Control:** A header containing category sorting toggles.
    * **Application Grid Flow:** An expansive grid built out of custom individual card widgets.

### Sorting & Filtering Paradigms
The sorting panel includes a segmented toggle block supporting three explicit operations:
* **Alphabetical:** Traditional lexigraphical string processing sorting `A-Z`.
* **Most Common:** Weights predefined flag parameters within the JSON schemas to prioritize baseline utilities (browsers, structural tools).
* **Reviews & Ratings (Stars):** Pulls rating attributes mapped from the JSON file or dynamically retrieved online from provider APIs to sort application layouts based on numerical customer ratings (1.0 to 5.0 stars).

### Custom App Card Component Specification
Every application row or grid block must compose the following elements safely:

```

┌────────────────────────────────────────────────────────┐
│  [ [Icon] ]  App Name               [x] Native (Avail) │
│              ★★★★★ (4.8)           [ ] Flatpak (Avail)│
│              Short description...   [ ] Snap (Unavail) │
└────────────────────────────────────────────────────────┘

```
* **Checkboxes:** Selecting an app checks the box corresponding to the top-tier active source framework determined by the engine, while offering granular dropdown parameters to manually override a source for an independent installation block.

---

## 6. Metadata Storage Schema (`apps.json`)
The application relies on a strictly typed JSON structure acting as its declarative inventory manifest.

```json
{
  "categories": {
    "development": {
      "display_name": "Development & Engineering",
      "icon_name": "developer-mode-symbolic",
      "apps": [
        {
          "id": "vscode",
          "name": "Visual Studio Code",
          "description": "Powerful code editor optimized for building modern web and cloud applications.",
          "stars": 4.7,
          "is_common": true,
          "sources": {
            "apt": "code",
            "dnf": "code",
            "pacman": "visual-studio-code-bin",
            "flatpak": "com.visualstudio.code",
            "snap": "code"
          }
        }
      ]
    },
    "multimedia": {
      "display_name": "Multimedia & Production",
      "icon_name": "audio-x-generic-symbolic",
      "apps": [
        {
          "id": "vlc",
          "name": "VLC Media Player",
          "description": "Free and open source cross-platform multimedia player and framework.",
          "stars": 4.9,
          "is_common": true,
          "sources": {
            "apt": "vlc",
            "dnf": "vlc",
            "pacman": "vlc",
            "flatpak": "org.videolan.VLC",
            "snap": "vlc"
          }
        }
      ]
    }
  }
}

```

---

## 7. Security & Error Handling Execution Specs

### Asynchronous Operations

To avoid locking or crashing the graphical interface thread during heavy tasks, all installation processes are executed within an asynchronous wrapper loop using Python’s `asyncio` framework or standard threads monitored via GLib timeouts (`GLib.timeout_add`).

### Administrative Token Elevation

* Commands requiring root permissions are isolated from the frontend.
* Standard terminal error pipes (`stderr`) are captured and printed inside a toggleable `Gtk.Expander` detailing terminal logging context in real-time. This keeps error logs accessible without confusing standard users.
"""


* after the users selects hes applications we should have an export file where this file later on could be opened by the software which will load all hes choises, in case he want to install the same things on another machine.
* should have all the needed categories and for starting lets add all the good known applications and lets make it pretty easy to add more apps later on.
