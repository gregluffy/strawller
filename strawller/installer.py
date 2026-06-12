"""Asynchronous installation service using threads and GLib callbacks."""

from __future__ import annotations

import subprocess
import threading
from typing import Callable

try:
    from gi.repository import GLib
    _HAVE_GLIB = True
except ImportError:
    _HAVE_GLIB = False


def _idle(fn, *args):
    """Schedule *fn* on the GLib main loop, or call directly if unavailable."""
    if _HAVE_GLIB:
        GLib.idle_add(fn, *args)
    else:
        fn(*args)


class InstallJob:
    """Represents a running installation process."""

    def __init__(self, label: str, cmd: list[str]):
        self.label = label
        self.cmd = cmd
        self._proc: subprocess.Popen | None = None

    def cancel(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()


class InstallerService:
    """Run installation batches in background threads.

    Callbacks are dispatched on the GLib main loop so UI widgets can be
    updated safely.

    Args:
        on_output: called with (label: str, line: str) for each stdout/stderr line.
        on_batch_done: called with (label: str, returncode: int) when a batch finishes.
        on_all_done: called with (unresolved: list[str]) when all batches complete.
    """

    def __init__(
        self,
        on_output: Callable[[str, str], None] | None = None,
        on_batch_done: Callable[[str, int], None] | None = None,
        on_all_done: Callable[[list[str]], None] | None = None,
    ):
        self._on_output = on_output or (lambda l, t: None)
        self._on_batch_done = on_batch_done or (lambda l, rc: None)
        self._on_all_done = on_all_done or (lambda u: None)
        self._jobs: list[InstallJob] = []
        self._lock = threading.Lock()

    def install(self, batches: dict) -> None:
        """Start installation in background threads. Returns immediately."""
        jobs = self._build_jobs(batches)
        unresolved = batches.get("unresolved", [])
        if not jobs:
            _idle(self._on_all_done, unresolved)
            return
        self._jobs = jobs
        thread = threading.Thread(
            target=self._run_all, args=(jobs, unresolved), daemon=True
        )
        thread.start()

    def cancel_all(self) -> None:
        with self._lock:
            for job in self._jobs:
                job.cancel()

    def _build_jobs(self, batches: dict) -> list[InstallJob]:
        jobs = []
        native = batches.get("native", {})
        if native.get("packages") and native.get("pkg_manager"):
            pm = native["pkg_manager"]
            pkgs = native["packages"]
            cmd = self._native_cmd(pm, pkgs)
            jobs.append(InstallJob(f"Native ({pm})", cmd))

        flatpak_pkgs = batches.get("flatpak", {}).get("packages", [])
        if flatpak_pkgs:
            cmd = ["flatpak", "install", "flathub", "-y"] + flatpak_pkgs
            jobs.append(InstallJob("Flatpak", cmd))

        snap_pkgs = batches.get("snap", {}).get("packages", [])
        if snap_pkgs:
            cmd = ["pkexec", "snap", "install"] + snap_pkgs
            jobs.append(InstallJob("Snap", cmd))

        return jobs

    @staticmethod
    def _native_cmd(pkg_manager: str, pkgs: list[str]) -> list[str]:
        if pkg_manager == "apt":
            return ["pkexec", "apt", "install", "-y"] + pkgs
        if pkg_manager == "dnf":
            return ["pkexec", "dnf", "install", "-y"] + pkgs
        if pkg_manager == "pacman":
            return ["pkexec", "pacman", "-S", "--noconfirm"] + pkgs
        return ["pkexec", pkg_manager, "install"] + pkgs

    def _run_all(self, jobs: list[InstallJob], unresolved: list[str]) -> None:
        for job in jobs:
            self._run_job(job)
        _idle(self._on_all_done, unresolved)

    def _run_job(self, job: InstallJob) -> None:
        try:
            proc = subprocess.Popen(
                job.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            with self._lock:
                job._proc = proc

            for line in proc.stdout:
                line = line.rstrip("\n")
                _idle(self._on_output, job.label, line)

            proc.wait()
            _idle(self._on_batch_done, job.label, proc.returncode)
        except OSError as exc:
            _idle(self._on_output, job.label, f"[error] {exc}")
            _idle(self._on_batch_done, job.label, -1)
