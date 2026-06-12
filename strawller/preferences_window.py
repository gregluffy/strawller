"""Preferences window for source priority order and settings."""

from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GObject

from .settings import load_settings, save_settings


_SOURCE_LABELS = {
    "flatpak": ("Flatpak", "org.flatpak.Flatpak-symbolic"),
    "native": ("Native Package Manager", "preferences-system-symbolic"),
    "snap": ("Snap", "package-x-generic-symbolic"),
}


class PreferencesWindow(Adw.PreferencesWindow):
    """Window for adjusting source priority and other settings."""

    __gsignals__ = {
        "order-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Preferences")
        self.set_default_size(480, 400)

        self._settings = load_settings()
        self._order: list[str] = self._settings.get(
            "source_order", ["flatpak", "native", "snap"]
        )

        page = Adw.PreferencesPage(title="General", icon_name="preferences-system-symbolic")
        self.add(page)

        # --- Source priority group ---
        group = Adw.PreferencesGroup(
            title="Installation Source Priority",
            description="Drag or use the arrows to reorder. The topmost source is tried first.",
        )
        page.add(group)

        self._rows: list[tuple[str, Adw.ActionRow]] = []
        for source in self._order:
            row = self._build_source_row(source)
            group.add(row)

        # --- Save button ---
        save_group = Adw.PreferencesGroup()
        page.add(save_group)

        save_row = Adw.ActionRow(title="Apply Changes")
        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("suggested-action")
        save_btn.set_valign(Gtk.Align.CENTER)
        save_btn.connect("clicked", self._on_save)
        save_row.add_suffix(save_btn)
        save_group.add(save_row)

    def _build_source_row(self, source: str) -> Adw.ActionRow:
        label, icon = _SOURCE_LABELS.get(source, (source.title(), "application-x-executable-symbolic"))
        row = Adw.ActionRow(title=label)
        row.set_icon_name(icon)

        up_btn = Gtk.Button.new_from_icon_name("go-up-symbolic")
        up_btn.add_css_class("flat")
        up_btn.set_valign(Gtk.Align.CENTER)
        up_btn.connect("clicked", self._on_move, source, -1)

        down_btn = Gtk.Button.new_from_icon_name("go-down-symbolic")
        down_btn.add_css_class("flat")
        down_btn.set_valign(Gtk.Align.CENTER)
        down_btn.connect("clicked", self._on_move, source, +1)

        row.add_suffix(up_btn)
        row.add_suffix(down_btn)
        self._rows.append((source, row))
        return row

    def _on_move(self, _btn, source: str, direction: int) -> None:
        idx = self._order.index(source)
        new_idx = idx + direction
        if 0 <= new_idx < len(self._order):
            self._order[idx], self._order[new_idx] = (
                self._order[new_idx],
                self._order[idx],
            )
            self._refresh_order_labels()

    def _refresh_order_labels(self) -> None:
        for i, (source, row) in enumerate(self._rows):
            pos = self._order.index(source)
            row.set_subtitle(f"Priority {pos + 1}")

    def _on_save(self, _btn) -> None:
        self._settings["source_order"] = self._order
        save_settings(self._settings)
        self.emit("order-changed")
        self.close()

    @property
    def current_order(self) -> list[str]:
        return list(self._order)
