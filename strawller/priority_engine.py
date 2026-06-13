"""Multi-source priority resolution and installation batch builder."""

from __future__ import annotations

DEFAULT_ORDER = ["flatpak", "native", "snap"]


class PriorityEngine:
    """Resolve the best package source for an app given system availability."""

    def __init__(self, profile: dict, order: list[str] | None = None):
        self._profile = profile
        self._order = order if order is not None else list(DEFAULT_ORDER)

    @property
    def order(self) -> list[str]:
        return list(self._order)

    @order.setter
    def order(self, value: list[str]) -> None:
        self._order = list(value)

    def _native_key(self) -> str | None:
        return self._profile.get("pkg_manager")

    def _source_available(self, source_type: str, app: dict) -> tuple[bool, str]:
        """Return (available, package_name) for a given source type."""
        sources = app.get("sources", {})
        if source_type == "flatpak":
            if self._profile.get("flatpak") and "flatpak" in sources:
                return True, sources["flatpak"]
        elif source_type == "snap":
            if self._profile.get("snap") and "snap" in sources:
                return True, sources["snap"]
        elif source_type == "native":
            pkg_manager = self._native_key()
            if pkg_manager and pkg_manager in sources:
                return True, sources[pkg_manager]
        return False, ""

    def resolve(self, app: dict, override: str | None = None) -> tuple[str | None, str | None]:
        """Return (source_type, package_name) for the best available source.

        *override* pins to a specific source type bypassing priority order.
        Returns (None, None) when no source is available.
        """
        if override:
            available, pkg = self._source_available(override, app)
            if available:
                return override, pkg
            return None, None

        for source_type in self._order:
            available, pkg = self._source_available(source_type, app)
            if available:
                return source_type, pkg
        return None, None

    def available_sources(self, app: dict) -> list[tuple[str, str]]:
        """Return all (source_type, package_name) pairs available for *app*."""
        results = []
        sources = app.get("sources", {})
        if self._profile.get("flatpak") and "flatpak" in sources:
            results.append(("flatpak", sources["flatpak"]))
        pkg_manager = self._native_key()
        if pkg_manager and pkg_manager in sources:
            results.append(("native", sources[pkg_manager]))
        if self._profile.get("snap") and "snap" in sources:
            results.append(("snap", sources["snap"]))
        return results

    def build_batches(
        self,
        selections: list[tuple[dict, str | None]],
    ) -> dict:
        """Group selected (app, override) pairs into installation batches.

        Returns:
            {
                "native":  {"pkg_manager": str, "packages": [str, ...]},
                "flatpak": {"packages": [str, ...]},
                "snap":    {"packages": [str, ...]},
                "unresolved": [app_id, ...]
            }
        """
        batches: dict = {
            "native": {"pkg_manager": self._native_key(), "packages": []},
            "flatpak": {"packages": []},
            "snap": {"packages": [], "classic": []},
            "unresolved": [],
        }
        for app, override in selections:
            source_type, pkg = self.resolve(app, override)
            if source_type == "native":
                batches["native"]["packages"].append(pkg)
            elif source_type == "flatpak":
                batches["flatpak"]["packages"].append(pkg)
            elif source_type == "snap":
                if app.get("sources", {}).get("snap_classic", False):
                    batches["snap"]["classic"].append(pkg)
                else:
                    batches["snap"]["packages"].append(pkg)
            else:
                batches["unresolved"].append(app.get("id", "?"))
        return batches
