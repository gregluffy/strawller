"""Installation progress dialog."""

from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from ..installer import InstallerService


class InstallDialog(Adw.Dialog):
    """Modal dialog showing per-batch progress and live log output."""

    def __init__(self, batches: dict, parent: Gtk.Widget):
        super().__init__()
        self.set_title("Installing Applications")
        self.set_content_width(600)
        self.set_content_height(480)

        self._batches = batches
        self._batch_bars: dict[str, Gtk.ProgressBar] = {}
        self._done_count = 0
        self._total_jobs = 0
        self._log_buffer = Gtk.TextBuffer()

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Header bar
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        root.append(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)

        # Per-batch progress rows
        progress_group = Adw.PreferencesGroup(title="Progress")
        for label, pkg_list in self._batch_label_map(batches):
            row_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

            row_label = Gtk.Label(
                label=f"{label}  ({len(pkg_list)} package{'s' if len(pkg_list) != 1 else ''})"
            )
            row_label.set_xalign(0)
            row_label.add_css_class("heading")
            row_box.append(row_label)

            bar = Gtk.ProgressBar()
            bar.set_pulse_step(0.1)
            row_box.append(bar)
            self._batch_bars[label] = bar
            self._total_jobs += 1

            row = Adw.ActionRow()
            row.set_child(row_box)
            progress_group.add(row)

        content.append(progress_group)

        # Log expander
        expander = Gtk.Expander(label="Show terminal output")
        expander.add_css_class("card")

        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(160)
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        log_view = Gtk.TextView(buffer=self._log_buffer)
        log_view.set_editable(False)
        log_view.set_cursor_visible(False)
        log_view.set_monospace(True)
        log_view.add_css_class("monospace")
        scroll.set_child(log_view)
        expander.set_child(scroll)
        content.append(expander)

        # Unresolved apps notice
        unresolved = batches.get("unresolved", [])
        if unresolved:
            warn = Adw.Banner(
                title=f"Could not resolve: {', '.join(unresolved)}",
                revealed=True,
            )
            warn.add_css_class("warning")
            content.append(warn)

        # Action buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)

        self._cancel_btn = Gtk.Button(label="Cancel")
        self._cancel_btn.add_css_class("destructive-action")
        self._cancel_btn.connect("clicked", self._on_cancel)
        btn_box.append(self._cancel_btn)

        self._close_btn = Gtk.Button(label="Close")
        self._close_btn.add_css_class("suggested-action")
        self._close_btn.set_sensitive(False)
        self._close_btn.connect("clicked", lambda _: self.close())
        btn_box.append(self._close_btn)

        content.append(btn_box)
        root.append(content)
        self.set_child(root)

        # Start installation
        self._service = InstallerService(
            on_output=self._on_output,
            on_batch_done=self._on_batch_done,
            on_all_done=self._on_all_done,
        )

        self._pulse_source = GLib.timeout_add(100, self._pulse_bars)
        self._service.install(batches)

    # ------------------------------------------------------------------

    @staticmethod
    def _batch_label_map(batches: dict) -> list[tuple[str, list]]:
        result = []
        native = batches.get("native", {})
        if native.get("packages") and native.get("pkg_manager"):
            pm = native["pkg_manager"]
            result.append((f"Native ({pm})", native["packages"]))
        flatpak_pkgs = batches.get("flatpak", {}).get("packages", [])
        if flatpak_pkgs:
            result.append(("Flatpak", flatpak_pkgs))
        snap_pkgs = batches.get("snap", {}).get("packages", [])
        if snap_pkgs:
            result.append(("Snap", snap_pkgs))
        snap_classic_pkgs = batches.get("snap", {}).get("classic", [])
        if snap_classic_pkgs:
            result.append(("Snap (classic)", snap_classic_pkgs))
        return result

    def _pulse_bars(self) -> bool:
        for bar in self._batch_bars.values():
            if bar.get_fraction() < 1.0:
                bar.pulse()
        return True

    def _stop_pulsing(self) -> None:
        if self._pulse_source:
            GLib.source_remove(self._pulse_source)
            self._pulse_source = None

    def _on_output(self, label: str, line: str) -> None:
        end = self._log_buffer.get_end_iter()
        self._log_buffer.insert(end, f"[{label}] {line}\n")

    def _on_batch_done(self, label: str, returncode: int) -> None:
        bar = self._batch_bars.get(label)
        if bar:
            bar.set_fraction(1.0)
        self._done_count += 1
        status = "✓" if returncode == 0 else f"✗ (exit {returncode})"
        end = self._log_buffer.get_end_iter()
        self._log_buffer.insert(end, f"--- {label} {status} ---\n")

    def _on_all_done(self, unresolved: list[str]) -> None:
        self._stop_pulsing()
        self._cancel_btn.set_sensitive(False)
        self._close_btn.set_sensitive(True)
        end = self._log_buffer.get_end_iter()
        self._log_buffer.insert(end, "\nAll done.\n")

    def _on_cancel(self, _btn) -> None:
        self._stop_pulsing()
        self._service.cancel_all()
        self._cancel_btn.set_sensitive(False)
        self._close_btn.set_sensitive(True)
