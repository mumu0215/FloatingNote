"""Windows startup registry helpers for Floating Note."""

from __future__ import annotations

import sys
from pathlib import Path

from src.paths import app_root, executable_path, is_frozen

APP_NAME = "FloatingNote"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _startup_command() -> str:
    if is_frozen():
        return f'"{executable_path()}"'

    root = app_root()
    main_py = root / "src" / "main.py"
    candidates = [
        root / ".venv" / "Scripts" / "pythonw.exe",
        root / ".venv" / "Scripts" / "python.exe",
        Path(sys.executable),
    ]
    pythonw = candidates[-1]
    for cand in candidates:
        if cand.exists():
            pythonw = cand
            break
    if pythonw.name.lower() == "python.exe":
        sibling = pythonw.with_name("pythonw.exe")
        if sibling.exists():
            pythonw = sibling
    return f'"{pythonw}" "{main_py}"'


def is_autostart_enabled() -> bool:
    try:
        import winreg
    except ImportError:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(value)
    except OSError:
        return False


def enable_autostart() -> bool:
    try:
        import winreg
    except ImportError:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _startup_command())
        return True
    except OSError:
        return False


def disable_autostart() -> bool:
    try:
        import winreg
    except ImportError:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False


def set_autostart(enabled: bool) -> bool:
    return enable_autostart() if enabled else disable_autostart()
