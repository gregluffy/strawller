"""Custom application card widget."""

from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject

_SOURCE_LABEL = {"flatpak": "Flatpak", "native": "Native", "snap": "Snap"}


def _resolve_icon(app: dict) -> str | None:
    """Return best icon name to try, or None to let Avatar show initials."""
    explicit = app.get("icon_name")
    if explicit:
        return explicit
    sources = app.get("sources", {})
    for key in ("apt", "dnf", "pacman"):
        pkg = sources.get(key, "")
        if pkg:
            return pkg
    return None


class AppCard(Gtk.Box):
    """Application card with avatar, info column, source pills, and install toggle.

    Layout:
        [Avatar] | Name / Stars / Desc / Source pills  |  [Source ▾]
                                                           [Add to install]

    Emits::
        toggled(app_id: str, source_type: str, active: bool)
    """

    __gsignals__ = {
        "toggled": (GObject.SignalFlags.RUN_FIRST, None, (str, str, bool)),
    }

    def __init__(
        self,
        app: dict,
        available_sources: list[tuple[str, str]],
        default_source: str | None,
    ):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self._app = app
        self._available_sources = available_sources
        self._current_source = default_source
        self._source_dropdown_keys: list[str] = []
        self._dropdown: Gtk.DropDown | None = None

        self.add_css_class("card")
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        self.set_margin_start(4)
        self.set_margin_end(4)

        # ── Left: avatar + info ──────────────────────────────────────
        left = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        left.set_hexpand(True)
        left.set_margin_top(12)
        left.set_margin_bottom(12)
        left.set_margin_start(12)
        left.set_margin_end(8)

        # Avatar — shows app icon if available, otherwise app name initials
        avatar = Adw.Avatar(size=48, text=app.get("name", "?"), show_initials=True)
        icon_name = _resolve_icon(app)
        if icon_name:
            avatar.set_icon_name(icon_name)
        avatar.set_valign(Gtk.Align.CENTER)
        left.append(avatar)

        # Info column
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info.set_hexpand(True)
        info.set_valign(Gtk.Align.CENTER)

        name_lbl = Gtk.Label(label=app.get("name", ""))
        name_lbl.add_css_class("heading")
        name_lbl.set_xalign(0)
        info.append(name_lbl)

        desc_lbl = Gtk.Label(label=app.get("description", ""))
        desc_lbl.add_css_class("caption")
        desc_lbl.add_css_class("dim-label")
        desc_lbl.set_xalign(0)
        desc_lbl.set_wrap(True)
        desc_lbl.set_max_width_chars(48)
        info.append(desc_lbl)

        # Source availability pills — accent for selected, dim for others
        if available_sources:
            pills = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            pills.set_margin_top(5)
            for stype, _ in available_sources:
                lbl = Gtk.Label(label=_SOURCE_LABEL[stype])
                lbl.add_css_class("caption")
                if stype == default_source:
                    lbl.add_css_class("accent")
                else:
                    lbl.add_css_class("dim-label")
                pills.append(lbl)
            info.append(pills)
        else:
            unavail = Gtk.Label(label="Not available for your system")
            unavail.add_css_class("caption")
            unavail.add_css_class("error")
            unavail.set_xalign(0)
            unavail.set_margin_top(4)
            info.append(unavail)

        left.append(info)
        self.append(left)

        # ── Separator ────────────────────────────────────────────────
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep.set_margin_top(10)
        sep.set_margin_bottom(10)
        self.append(sep)

        # ── Right: source selector + install toggle ───────────────────
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        right.set_valign(Gtk.Align.CENTER)
        right.set_halign(Gtk.Align.CENTER)
        right.set_margin_top(12)
        right.set_margin_bottom(12)
        right.set_margin_start(14)
        right.set_margin_end(14)
        right.set_size_request(148, -1)

        if len(available_sources) > 1:
            model = Gtk.StringList()
            for stype, _ in available_sources:
                model.append(_SOURCE_LABEL[stype])
                self._source_dropdown_keys.append(stype)
            self._dropdown = Gtk.DropDown(model=model)
            self._dropdown.set_tooltip_text("Choose installation source")
            if default_source in self._source_dropdown_keys:
                self._dropdown.set_selected(
                    self._source_dropdown_keys.index(default_source)
                )
            self._dropdown.connect("notify::selected", self._on_dropdown_changed)
            right.append(self._dropdown)
        elif available_sources:
            self._source_dropdown_keys = [available_sources[0][0]]
            via_lbl = Gtk.Label(
                label=f"via {_SOURCE_LABEL[available_sources[0][0]]}"
            )
            via_lbl.add_css_class("caption")
            via_lbl.add_css_class("dim-label")
            right.append(via_lbl)

        self._install_btn = Gtk.ToggleButton(label="Add to install")
        self._install_btn.set_sensitive(bool(available_sources))
        if available_sources:
            self._install_btn.add_css_class("suggested-action")
        self._install_btn.connect("toggled", self._on_install_toggled)
        right.append(self._install_btn)

        self.append(right)

    # ------------------------------------------------------------------

    @property
    def app_id(self) -> str:
        return self._app.get("id", "")

    @property
    def is_selected(self) -> bool:
        return self._install_btn.get_active()

    @property
    def selected_source(self) -> str | None:
        if self._dropdown:
            idx = self._dropdown.get_selected()
            if 0 <= idx < len(self._source_dropdown_keys):
                return self._source_dropdown_keys[idx]
        return self._current_source

    def set_selected(self, active: bool) -> None:
        self._install_btn.set_active(active)

    def _on_install_toggled(self, btn: Gtk.ToggleButton) -> None:
        active = btn.get_active()
        btn.set_label("Added ✓" if active else "Add to install")
        self.emit("toggled", self.app_id, self.selected_source or "", active)

    def _on_dropdown_changed(self, dropdown: Gtk.DropDown, _param) -> None:
        idx = dropdown.get_selected()
        if 0 <= idx < len(self._source_dropdown_keys):
            self._current_source = self._source_dropdown_keys[idx]
