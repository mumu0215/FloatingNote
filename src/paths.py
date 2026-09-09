"""Resolve app root and persistent user data paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "FloatingNote"


def is_frozen() -> bool:
    """True when running as a packaged binary (Nuitka / PyInstaller)."""
    if getattr(sys, "frozen", False):
        return True
    if os.environ.get("NUITKA_ONEFILE_PARENT"):
        return True
    # Nuitka sets this on compiled modules at runtime
    main = sys.modules.get("__main__")
    if main is not None and getattr(main, "__compiled__", None) is not None:
        return True
    exe = Path(sys.executable).name.lower()
    return exe.endswith(".exe") and exe not in ("python.exe", "pythonw.exe")


def app_root() -> Path:
    """Install / source root (exe folder when frozen, repo root in dev)."""
    if is_frozen():
        # Nuitka onefile: original path is usually sys.argv[0]
        for raw in (sys.argv[0] if sys.argv else "", sys.executable):
            if not raw:
                continue
            p = Path(raw)
            try:
                p = p.resolve()
            except OSError:
                continue
            if p.suffix.lower() == ".exe":
                return p.parent
            if p.is_file():
                return p.parent
        return Path.cwd()
    return Path(__file__).resolve().parent.parent


def user_data_dir() -> Path:
    """Persistent data dir that survives reinstall / rebuild.

    Override with env ``FLOATING_NOTE_DATA`` if needed.
    Default: ``%LOCALAPPDATA%\\FloatingNote`` on Windows.
    """
    override = (os.environ.get("FLOATING_NOTE_DATA") or "").strip()
    if override:
        return Path(override).expanduser()

    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / APP_DIR_NAME
        return Path.home() / "AppData" / "Local" / APP_DIR_NAME

    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / APP_DIR_NAME
    return Path.home() / ".local" / "share" / APP_DIR_NAME


def executable_path() -> Path:
    """Path used for autostart registry entry."""
    if is_frozen():
        for raw in (sys.argv[0] if sys.argv else "", sys.executable):
            if not raw:
                continue
            p = Path(raw)
            try:
                p = p.resolve()
            except OSError:
                continue
            if p.suffix.lower() == ".exe":
                return p
        return Path(sys.executable).resolve()
    return Path(sys.executable).resolve()
