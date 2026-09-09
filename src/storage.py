"""Persist notes and window config to local JSON files."""

from __future__ import annotations

import json
import shutil
import threading
import uuid
from pathlib import Path
from typing import Any

from src.paths import app_root, user_data_dir

DATA_DIR = user_data_dir()
NOTES_FILE = DATA_DIR / "notes.json"
CONFIG_FILE = DATA_DIR / "config.json"
PID_FILE = DATA_DIR / "floating_note.pid"

_DEFAULT_CONFIG: dict[str, Any] = {
    "width": 300,
    "height": 480,
    "x": None,
    "y": None,
    "opacity": 0.92,
    "autostart": True,
    "max_preview_chars": 120,
    "always_on_top": True,
}

_lock = threading.Lock()
_migrated = False


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _migrate_legacy_data()


def _legacy_data_dirs() -> list[Path]:
    """Older locations that stored notes next to the install / source tree."""
    root = app_root()
    candidates = [
        root / "data",
        root.parent / "data",  # e.g. release/FloatingNote -> project data/
    ]
    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[Path] = []
    for path in candidates:
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
        if key in seen:
            continue
        seen.add(key)
        # Never treat the new user data dir as a legacy source
        try:
            if path.resolve() == DATA_DIR.resolve():
                continue
        except OSError:
            if path == DATA_DIR:
                continue
        out.append(path)
    return out


def _file_has_usable_notes(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False
    if not isinstance(raw, list):
        return False
    for item in raw:
        if isinstance(item, dict) and str(item.get("text", "")).strip():
            return True
    return False


def _copy_if_missing(src: Path, dest: Path) -> None:
    if dest.exists() or not src.is_file():
        return
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    except OSError:
        pass


def _migrate_legacy_data() -> None:
    """One-time copy from install-folder data/ into the persistent user dir."""
    global _migrated
    if _migrated:
        return
    _migrated = True

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        return

    # Prefer a legacy notes file that actually contains notes
    if not NOTES_FILE.exists():
        chosen: Path | None = None
        for legacy in _legacy_data_dirs():
            candidate = legacy / "notes.json"
            if _file_has_usable_notes(candidate):
                chosen = candidate
                break
            if chosen is None and candidate.is_file():
                chosen = candidate
        if chosen is not None:
            _copy_if_missing(chosen, NOTES_FILE)

    if not CONFIG_FILE.exists():
        for legacy in _legacy_data_dirs():
            candidate = legacy / "config.json"
            if candidate.is_file():
                _copy_if_missing(candidate, CONFIG_FILE)
                break


def _read_json(path: Path, default: Any) -> Any:
    ensure_data_dir()
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, data: Any) -> None:
    ensure_data_dir()
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def load_config() -> dict[str, Any]:
    with _lock:
        raw = _read_json(CONFIG_FILE, {})
        cfg = dict(_DEFAULT_CONFIG)
        if isinstance(raw, dict):
            cfg.update(raw)
        return cfg


def save_config(config: dict[str, Any]) -> None:
    with _lock:
        merged = dict(_DEFAULT_CONFIG)
        merged.update(config)
        _write_json(CONFIG_FILE, merged)


def load_notes() -> list[dict[str, Any]]:
    with _lock:
        raw = _read_json(NOTES_FILE, [])
        if not isinstance(raw, list):
            return []
        notes: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            notes.append(
                {
                    "id": str(item.get("id") or uuid.uuid4()),
                    "text": text,
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at"),
                }
            )
        return notes


def save_notes(notes: list[dict[str, Any]]) -> None:
    with _lock:
        payload = []
        for item in notes:
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            payload.append(
                {
                    "id": str(item.get("id") or uuid.uuid4()),
                    "text": text,
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at"),
                }
            )
        _write_json(NOTES_FILE, payload)


def new_note_id() -> str:
    return str(uuid.uuid4())
