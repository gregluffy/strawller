"""Custom application card widget."""

from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GObject


def _star_string(rating: float) -> str:
    full = int(round(rating))
    full = max(0, min(5, full))
    return "★" * full + "☆" * (5 - full) + f"  {rating:.1f}"


class AppCard(Gtk.Box):
    """Card widget representing a single installable application.

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
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self._app = app
        self._available_sources = available_sources
        self._selected = False
        self._current_source = default_source

        self.add_css_class("card")
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        self.set_margin_start(4)
        self.set_margin_end(4)

        # --- Icon ---
        icon = Gtk.Image.new_from_icon_name(
            app.get("icon_name", "application-x-executable-symbolic")
        )
        icon.set_icon_size(Gtk.IconSize.LARGE)
        icon.set_pixel_size(48)
        icon.set_valign(Gtk.Align.CENTER)
        icon.set_margin_start(8)
        self.append(icon)

        # --- Info column ---
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_hexpand(True)
        info_box.set_valign(Gtk.Align.CENTER)
        info_box.set_margin_top(8)
        info_box.set_margin_bottom(8)

        name_label = Gtk.Label(label=app.get("name", ""))
        name_label.add_css_class("heading")
        name_label.set_xalign(0)
        info_box.append(name_label)

        stars_label = Gtk.Label(label=_star_string(app.get("stars", 0.0)))
        stars_label.add_css_class("caption")
        stars_label.set_xalign(0)
        info_box.append(stars_label)

        desc_label = Gtk.Label(label=app.get("description", ""))
        desc_label.add_css_class("caption-heading" if False else "body")
        desc_label.add_css_class("dim-label")
        desc_label.set_xalign(0)
        desc_label.set_wrap(True)
        desc_label.set_max_width_chars(45)
        info_box.append(desc_label)

        self.append(info_box)

        # --- Source selection column ---
        source_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        source_box.set_valign(Gtk.Align.CENTER)
        source_box.set_margin_end(8)

        source_labels = {"flatpak": "Flatpak", "native": "Native", "snap": "Snap"}
        available_keys = {s for s, _ in available_sources}

        self._source_dropdown_model = Gtk.StringList()
        self._source_dropdown_keys: list[str] = []

        for source_type in ("flatpak", "native", "snap"):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            label_text = source_labels[source_type]
            if source_type in available_keys:
                self._source_dropdown_model.append(label_text)
                self._source_dropdown_keys.append(source_type)
                badge = Gtk.Label(label=label_text)
                badge.add_css_class("caption")
            else:
                badge = Gtk.Label(label=f"{label_text} (unavail)")
                badge.add_css_class("caption")
                badge.add_css_class("dim-label")
            row.append(badge)
            source_box.append(row)

        # Source override dropdown (only shown when >1 source available)
        if len(available_sources) > 1:
            self._dropdown = Gtk.DropDown(
                model=self._source_dropdown_model,
            )
            self._dropdown.set_tooltip_text("Override install source")
            if default_source in self._source_dropdown_keys:
                self._dropdown.set_selected(
                    self._source_dropdown_keys.index(default_source)
                )
            self._dropdown.connect("notify::selected", self._on_dropdown_changed)
            source_box.append(self._dropdown)
        else:
            self._dropdown = None

        self.append(source_box)

        # --- Select checkbox ---
        self._check = Gtk.CheckButton()
        self._check.set_valign(Gtk.Align.CENTER)
        self._check.set_margin_end(8)
        self._check.set_sensitive(bool(available_sources))
        self._check.connect("toggled", self._on_check_toggled)
        self.append(self._check)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def app_id(self) -> str:
        return self._app.get("id", "")

    @property
    def is_selected(self) -> bool:
        return self._check.get_active()

    @property
    def selected_source(self) -> str | None:
        if self._dropdown:
            idx = self._dropdown.get_selected()
            if 0 <= idx < len(self._source_dropdown_keys):
                return self._source_dropdown_keys[idx]
        return self._current_source

    def set_selected(self, active: bool) -> None:
        self._check.set_active(active)

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def _on_check_toggled(self, check: Gtk.CheckButton) -> None:
        source = self.selected_source or ""
        self.emit("toggled", self.app_id, source, check.get_active())

    def _on_dropdown_changed(self, dropdown: Gtk.DropDown, _param) -> None:
        idx = dropdown.get_selected()
        if 0 <= idx < len(self._source_dropdown_keys):
            self._current_source = self._source_dropdown_keys[idx]
