"""Main application window."""

from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from .data_loader import load_apps, get_default_path, get_categories, get_apps_for_category
from .system_probe import get_system_profile
from .priority_engine import PriorityEngine
from .settings import load_settings
from .preferences_window import PreferencesWindow
from .widgets.app_card import AppCard
from .widgets.install_dialog import InstallDialog
from . import profile_io


class StrawllerWindow(Adw.ApplicationWindow):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Strawller")
        self.set_default_size(1100, 720)

        # --- State ---
        self._data = load_apps(get_default_path())
        self._profile = get_system_profile()
        settings = load_settings()
        self._engine = PriorityEngine(self._profile, settings.get("source_order"))
        self._categories = get_categories(self._data)
        self._active_category_id: str | None = None
        self._selections: dict[str, str | None] = {}  # app_id -> source_override
        self._cards: list[AppCard] = []
        self._sort_mode = "common"
        self._search_text = ""

        self._build_ui()
        GLib.idle_add(self._select_first_category)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        split = Adw.NavigationSplitView()
        split.set_min_sidebar_width(220)
        split.set_max_sidebar_width(280)

        # ---- Sidebar ----
        sidebar_page = Adw.NavigationPage(title="Categories")
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        sidebar_header = Adw.HeaderBar()
        sidebar_header.set_show_end_title_buttons(False)

        search_entry = Gtk.SearchEntry()
        search_entry.set_hexpand(True)
        search_entry.set_placeholder_text("Search apps…")
        search_entry.connect("search-changed", self._on_search_changed)
        self._search_entry = search_entry
        sidebar_header.set_title_widget(search_entry)
        sidebar_box.append(sidebar_header)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._cat_listbox = Gtk.ListBox()
        self._cat_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._cat_listbox.add_css_class("navigation-sidebar")
        self._cat_listbox.connect("row-selected", self._on_category_selected)

        for cat in self._categories:
            row = self._build_category_row(cat)
            self._cat_listbox.append(row)

        scroll.set_child(self._cat_listbox)
        sidebar_box.append(scroll)

        # Preferences button
        prefs_btn = Gtk.Button()
        prefs_btn.set_icon_name("preferences-system-symbolic")
        prefs_btn.set_tooltip_text("Preferences")
        prefs_btn.add_css_class("flat")
        prefs_btn.set_margin_top(4)
        prefs_btn.set_margin_bottom(8)
        prefs_btn.set_margin_start(8)
        prefs_btn.set_margin_end(8)
        prefs_btn.connect("clicked", self._on_open_prefs)
        sidebar_box.append(prefs_btn)

        sidebar_page.set_child(sidebar_box)
        split.set_sidebar(sidebar_page)

        # ---- Content panel ----
        content_page = Adw.NavigationPage(title="Applications")
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        content_header = Adw.HeaderBar()
        content_header.set_hexpand(True)

        # Distro banner label
        distro_label = Gtk.Label(
            label=self._distro_banner_text()
        )
        distro_label.add_css_class("caption")
        distro_label.add_css_class("dim-label")
        content_header.set_title_widget(distro_label)

        # Sorting toggle group
        sort_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        sort_box.add_css_class("linked")

        self._sort_btns: dict[str, Gtk.ToggleButton] = {}
        sort_defs = [
            ("common", "Common"),
            ("alpha", "A–Z"),
        ]
        first = None
        for key, label in sort_defs:
            btn = Gtk.ToggleButton(label=label)
            if first is None:
                first = btn
                btn.set_active(key == self._sort_mode)
            else:
                btn.set_group(first)
                btn.set_active(key == self._sort_mode)
            btn.connect("toggled", self._on_sort_toggled, key)
            sort_box.append(btn)
            self._sort_btns[key] = btn

        content_header.pack_end(sort_box)
        content_box.append(content_header)

        # Stack: loading spinner / app grid
        self._content_stack = Gtk.Stack()
        self._content_stack.set_vexpand(True)
        self._content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._content_stack.set_transition_duration(120)

        loading_box = Gtk.Box()
        loading_box.set_halign(Gtk.Align.CENTER)
        loading_box.set_valign(Gtk.Align.CENTER)
        spinner = Gtk.Spinner()
        spinner.set_size_request(48, 48)
        spinner.start()
        loading_box.append(spinner)
        self._content_stack.add_named(loading_box, "loading")

        grid_scroll = Gtk.ScrolledWindow()
        grid_scroll.set_vexpand(True)
        grid_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._flowbox = Gtk.FlowBox()
        self._flowbox.set_valign(Gtk.Align.START)
        self._flowbox.set_max_children_per_line(2)
        self._flowbox.set_min_children_per_line(1)
        self._flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._flowbox.set_row_spacing(4)
        self._flowbox.set_column_spacing(4)
        self._flowbox.set_margin_top(8)
        self._flowbox.set_margin_bottom(8)
        self._flowbox.set_margin_start(8)
        self._flowbox.set_margin_end(8)
        self._flowbox.set_filter_func(self._filter_card)

        grid_scroll.set_child(self._flowbox)
        self._content_stack.add_named(grid_scroll, "content")
        self._content_stack.set_visible_child_name("content")
        content_box.append(self._content_stack)

        # Action bar
        action_bar = Gtk.ActionBar()
        self._install_btn = Gtk.Button(label="Install Selected (0)")
        self._install_btn.add_css_class("suggested-action")
        self._install_btn.set_sensitive(False)
        self._install_btn.connect("clicked", self._on_install_clicked)
        action_bar.pack_start(self._install_btn)

        export_btn = Gtk.Button(label="Export Profile")
        export_btn.connect("clicked", self._on_export_clicked)
        action_bar.pack_end(export_btn)

        import_btn = Gtk.Button(label="Import Profile")
        import_btn.connect("clicked", self._on_import_clicked)
        action_bar.pack_end(import_btn)

        content_box.append(action_bar)
        content_page.set_child(content_box)
        split.set_content(content_page)

        self.set_content(split)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _distro_banner_text(self) -> str:
        name = self._profile.get("pretty_name", "Unknown Linux")
        pm = self._profile.get("pkg_manager")
        sources = []
        if pm:
            sources.append(pm)
        if self._profile.get("flatpak"):
            sources.append("Flatpak")
        if self._profile.get("snap"):
            sources.append("Snap")
        suffix = "  ·  " + " + ".join(sources) if sources else ""
        return f"{name}{suffix}"

    def _build_category_row(self, cat: dict) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.set_name(cat["id"])

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        icon = Gtk.Image.new_from_icon_name(cat.get("icon_name", "folder-symbolic"))
        icon.set_pixel_size(16)
        box.append(icon)

        label = Gtk.Label(label=cat["display_name"])
        label.set_xalign(0)
        label.set_hexpand(True)
        box.append(label)

        row.set_child(box)
        return row

    def _select_first_category(self) -> bool:
        if self._categories:
            first_row = self._cat_listbox.get_row_at_index(0)
            if first_row:
                self._cat_listbox.select_row(first_row)
        return False  # remove idle callback

    def _populate_grid(self, category_id: str) -> None:
        self._content_stack.set_visible_child_name("loading")
        GLib.idle_add(self._do_populate_grid, category_id)

    def _do_populate_grid(self, category_id: str) -> bool:
        if category_id != self._active_category_id:
            self._content_stack.set_visible_child_name("content")
            return False

        child = self._flowbox.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._flowbox.remove(child)
            child = nxt
        self._cards.clear()

        apps = get_apps_for_category(self._data, category_id)
        apps = self._sort_apps(apps)

        for app in apps:
            avail = self._engine.available_sources(app)
            source_type, _ = self._engine.resolve(app)
            card = AppCard(app, avail, source_type)
            if app["id"] in self._selections:
                card.set_selected(True)
            card.connect("toggled", self._on_card_toggled)
            self._flowbox.append(card)
            self._cards.append(card)

        self._flowbox.invalidate_filter()
        self._content_stack.set_visible_child_name("content")
        return False

    def _sort_apps(self, apps: list[dict]) -> list[dict]:
        if self._sort_mode == "alpha":
            return sorted(apps, key=lambda a: a.get("name", "").lower())
        # "common" — is_common first, then alphabetical
        return sorted(apps, key=lambda a: (not a.get("is_common", False), a.get("name", "").lower()))

    def _filter_card(self, child: Gtk.FlowBoxChild) -> bool:
        if not self._search_text:
            return True
        card = child.get_child()
        if not isinstance(card, AppCard):
            return True
        app = card._app
        needle = self._search_text.lower()
        return (
            needle in app.get("name", "").lower()
            or needle in app.get("description", "").lower()
        )

    def _update_install_button(self) -> None:
        count = len(self._selections)
        self._install_btn.set_label(f"Install Selected ({count})")
        self._install_btn.set_sensitive(count > 0)

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def _on_category_selected(self, listbox, row) -> None:
        if row is None:
            return
        cat_id = row.get_name()
        if cat_id != self._active_category_id:
            self._active_category_id = cat_id
            self._populate_grid(cat_id)

    def _on_sort_toggled(self, btn: Gtk.ToggleButton, key: str) -> None:
        if btn.get_active():
            self._sort_mode = key
            if self._active_category_id:
                self._populate_grid(self._active_category_id)

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self._search_text = entry.get_text()
        self._flowbox.invalidate_filter()

    def _on_card_toggled(self, card: AppCard, app_id: str, source: str, active: bool) -> None:
        if active:
            self._selections[app_id] = source or None
        else:
            self._selections.pop(app_id, None)
        self._update_install_button()

    def _on_install_clicked(self, _btn) -> None:
        from .data_loader import find_app_by_id
        selections = []
        for app_id, override in self._selections.items():
            app = find_app_by_id(self._data, app_id)
            if app:
                selections.append((app, override))
        batches = self._engine.build_batches(selections)
        dialog = InstallDialog(batches, parent=self)
        dialog.present(self)

    def _on_open_prefs(self, _btn) -> None:
        prefs = PreferencesWindow(transient_for=self)
        prefs.connect("order-changed", self._on_prefs_order_changed)
        prefs.present()

    def _on_prefs_order_changed(self, prefs_win: PreferencesWindow) -> None:
        self._engine.order = prefs_win.current_order
        if self._active_category_id:
            self._populate_grid(self._active_category_id)

    def _on_export_clicked(self, _btn) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Export Profile")
        dialog.set_initial_name("strawller-profile.json")
        dialog.save(self, None, self._on_export_response)

    def _on_export_response(self, dialog, result) -> None:
        try:
            file = dialog.save_finish(result)
            if file:
                profile_io.export_profile(self._selections, file.get_path())
        except Exception:
            pass

    def _on_import_clicked(self, _btn) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Import Profile")
        dialog.open(self, None, self._on_import_response)

    def _on_import_response(self, dialog, result) -> None:
        try:
            file = dialog.open_finish(result)
            if file:
                selections = profile_io.import_profile(file.get_path())
                self._selections = selections
                self._update_install_button()
                if self._active_category_id:
                    self._populate_grid(self._active_category_id)
        except Exception:
            pass
