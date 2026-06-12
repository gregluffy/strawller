"""Strawller application entry point."""

import sys

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw

from .window import StrawllerWindow


class StrawllerApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="io.github.strawller")

    def do_activate(self):
        win = self.get_active_window()
        if win is None:
            win = StrawllerWindow(application=self)
        win.present()


def main():
    app = StrawllerApp()
    return app.run(sys.argv)
