"""Floating Note - Windows desktop floating note tool.

Features:
- Always-on-top floating window
- Note blocks with truncated preview
- Click block to copy full text
- Right-click block to edit / delete
- Resizable window; size is persisted
- System tray resident + Windows autostart
"""

from __future__ import annotations

import datetime as dt
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Callable

# Allow `python src/main.py` without installing as package
_SRC_ROOT = Path(__file__).resolve().parent.parent
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from src import storage  # noqa: E402
from src.autostart import is_autostart_enabled, set_autostart  # noqa: E402
from src.paths import app_root  # noqa: E402
from src.storage import PID_FILE  # noqa: E402

APP_TITLE = "悬浮笔记"
RESIZE_BORDER = 6

# Visual tokens
BG = "#1e1e2e"
BG_PANEL = "#252536"
BG_BLOCK = "#2d2d44"
BG_BLOCK_HOVER = "#3a3a55"
BG_HEADER = "#181825"
FG = "#cdd6f4"
FG_MUTED = "#a6adc8"
ACCENT = "#89b4fa"
ACCENT_DIM = "#6c8ebf"
DANGER = "#f38ba8"
BORDER = "#45475a"
SUCCESS = "#a6e3a1"


def _now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _truncate(text: str, max_chars: int) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    flat = " ".join(line.strip() for line in text.split("\n") if line.strip())
    if not flat:
        flat = text.strip()
    if len(flat) <= max_chars:
        return flat
    return flat[: max(0, max_chars - 1)].rstrip() + "…"


def _write_pid() -> None:
    try:
        storage.ensure_data_dir()
        PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    except OSError:
        pass


def _clear_pid() -> None:
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except OSError:
        pass


class NoteEditDialog(tk.Toplevel):
    """Modal dialog for creating / editing a note. Save button is always pinned at bottom."""

    def __init__(
        self,
        master: tk.Misc,
        title: str,
        initial: str = "",
        on_save: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master)
        self.title(title)
        self.configure(bg=BG)
        self.resizable(True, True)
        self.transient(master)
        self.attributes("-topmost", True)
        self.grab_set()
        self.result: str | None = None
        self._on_save = on_save

        self.geometry("440x320")
        self.minsize(360, 260)

        # Pack bottom bar FIRST so it never gets squeezed off-screen
        btn_row = tk.Frame(self, bg=BG_PANEL, height=52)
        btn_row.pack(side="bottom", fill="x")
        btn_row.pack_propagate(False)

        hint = tk.Label(
            btn_row,
            text="Ctrl+Enter 也可保存",
            bg=BG_PANEL,
            fg=FG_MUTED,
            font=("Microsoft YaHei UI", 8),
        )
        hint.pack(side="left", padx=12)

        cancel_btn = tk.Button(
            btn_row,
            text="取消",
            command=self._cancel,
            bg=BG_BLOCK,
            fg=FG,
            activebackground=BG_BLOCK_HOVER,
            activeforeground=FG,
            relief="flat",
            padx=16,
            pady=6,
            cursor="hand2",
            font=("Microsoft YaHei UI", 10),
        )
        cancel_btn.pack(side="right", padx=(0, 12), pady=8)

        save_btn = tk.Button(
            btn_row,
            text="保存",
            command=self._save,
            bg=ACCENT,
            fg="#11111b",
            activebackground=ACCENT_DIM,
            activeforeground="#11111b",
            relief="flat",
            padx=22,
            pady=6,
            cursor="hand2",
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        save_btn.pack(side="right", padx=(0, 8), pady=8)

        header = tk.Label(
            self,
            text=title,
            bg=BG,
            fg=FG,
            font=("Microsoft YaHei UI", 11, "bold"),
            anchor="w",
        )
        header.pack(fill="x", padx=14, pady=(12, 6))

        frame = tk.Frame(self, bg=BG)
        frame.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        self.text = tk.Text(
            frame,
            wrap="word",
            bg=BG_BLOCK,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            font=("Microsoft YaHei UI", 10),
            padx=8,
            pady=8,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        self.text.pack(fill="both", expand=True, side="left")
        scroll = ttk.Scrollbar(frame, command=self.text.yview)
        scroll.pack(side="right", fill="y")
        self.text.configure(yscrollcommand=scroll.set)
        if initial:
            self.text.insert("1.0", initial)

        self.bind("<Escape>", lambda _e: self._cancel())
        self.bind("<Control-Return>", lambda _e: self._save())
        self.text.bind("<Control-Return>", lambda _e: self._save())
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.text.focus_set()
        self._center_on_parent(master)
        self.lift()
        self.focus_force()

    def _center_on_parent(self, master: tk.Misc) -> None:
        self.update_idletasks()
        try:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            w = max(self.winfo_width(), 440)
            h = max(self.winfo_height(), 320)
            try:
                px = master.winfo_rootx()
                py = master.winfo_rooty()
                pw = master.winfo_width()
                ph = master.winfo_height()
                x = px + max(0, (pw - w) // 2)
                y = py + max(0, (ph - h) // 2)
            except tk.TclError:
                x = (sw - w) // 2
                y = (sh - h) // 3
            # Keep fully on screen
            x = max(8, min(x, sw - w - 8))
            y = max(8, min(y, sh - h - 8))
            self.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass

    def _save(self) -> None:
        value = self.text.get("1.0", "end-1c").strip()
        if not value:
            messagebox.showwarning(APP_TITLE, "笔记内容不能为空。", parent=self)
            return
        self.result = value
        if self._on_save:
            self._on_save(value)
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class NoteBlock(tk.Frame):
    """Single note card in the floating list."""

    def __init__(
        self,
        master: tk.Misc,
        note: dict[str, Any],
        max_preview_chars: int,
        on_copy: Callable[[dict[str, Any]], None],
        on_edit: Callable[[dict[str, Any]], None],
        on_delete: Callable[[dict[str, Any]], None],
    ) -> None:
        super().__init__(
            master,
            bg=BG_BLOCK,
            highlightthickness=1,
            highlightbackground=BORDER,
            cursor="hand2",
        )
        self.note = note
        self._on_copy = on_copy
        self._on_edit = on_edit
        self._on_delete = on_delete

        preview = _truncate(str(note.get("text", "")), max_preview_chars)
        self.label = tk.Label(
            self,
            text=preview,
            bg=BG_BLOCK,
            fg=FG,
            font=("Microsoft YaHei UI", 9),
            justify="left",
            anchor="nw",
            wraplength=220,
            padx=10,
            pady=8,
        )
        self.label.pack(fill="both", expand=True)

        for widget in (self, self.label):
            widget.bind("<Button-1>", self._handle_left_click)
            widget.bind("<Button-3>", self._handle_right_click)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

        self.menu = tk.Menu(
            self,
            tearoff=0,
            bg=BG_PANEL,
            fg=FG,
            activebackground=ACCENT,
            activeforeground="#11111b",
            font=("Microsoft YaHei UI", 9),
        )
        self.menu.add_command(label="复制", command=lambda: self._on_copy(self.note))
        self.menu.add_command(label="编辑笔记", command=lambda: self._on_edit(self.note))
        self.menu.add_separator()
        self.menu.add_command(label="删除", command=lambda: self._on_delete(self.note))

    def _on_enter(self, _event: tk.Event | None = None) -> None:
        self.configure(bg=BG_BLOCK_HOVER, highlightbackground=ACCENT)
        self.label.configure(bg=BG_BLOCK_HOVER)

    def _on_leave(self, _event: tk.Event | None = None) -> None:
        self.configure(bg=BG_BLOCK, highlightbackground=BORDER)
        self.label.configure(bg=BG_BLOCK)

    def _handle_left_click(self, _event: tk.Event) -> None:
        self._on_copy(self.note)

    def _handle_right_click(self, event: tk.Event) -> None:
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def set_wraplength(self, width: int) -> None:
        # leave padding for card chrome
        self.label.configure(wraplength=max(80, width - 40))


class FloatingNoteApp:
    def __init__(self) -> None:
        self.config = storage.load_config()
        self.notes: list[dict[str, Any]] = storage.load_notes()
        self._blocks: list[NoteBlock] = []
        self._toast_after: str | None = None
        self._resize_save_after: str | None = None
        self._tray = None
        self._tray_thread: threading.Thread | None = None
        self._closing = False
        self._drag_start: tuple[int, int] | None = None
        self._resize_edge: str | None = None
        self._resize_start: tuple[int, int, int, int, int, int] | None = None
        # Compact floating window: allow shrinking well below default size.
        # Chrome (grip + composer + status + resize) is ~140px; list can collapse.
        self._min_w = 180
        self._min_h = 150

        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.configure(bg=BG)
        # No system title bar / min / max / close chrome
        self.root.overrideredirect(True)
        self._apply_window_icon()

        width = int(self.config.get("width") or 300)
        height = int(self.config.get("height") or 480)
        x = self.config.get("x")
        y = self.config.get("y")
        if x is None or y is None:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = max(0, sw - width - 24)
            y = max(0, (sh - height) // 4)
        self.root.geometry(f"{width}x{height}+{int(x)}+{int(y)}")

        if self.config.get("always_on_top", True):
            self.root.attributes("-topmost", True)
        try:
            opacity = float(self.config.get("opacity", 0.92))
            self.root.attributes("-alpha", max(0.5, min(1.0, opacity)))
        except (TypeError, ValueError, tk.TclError):
            pass

        self._build_ui()
        self._render_notes()
        self._bind_events()

        # Keep autostart registry entry in sync (dev python path or frozen exe)
        if self.config.get("autostart", True):
            if set_autostart(True):
                self.config["autostart"] = True
                storage.save_config(self.config)

        _write_pid()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close_window)
        self.root.after(200, self._start_tray)

    def _icon_candidates(self) -> list[Path]:
        roots = [app_root()]
        try:
            roots.append(Path(__file__).resolve().parent.parent)
        except OSError:
            pass
        names = ("app.ico", "app.png")
        out: list[Path] = []
        seen: set[str] = set()
        for root in roots:
            for name in names:
                path = root / "assets" / name
                key = str(path)
                if key in seen:
                    continue
                seen.add(key)
                out.append(path)
        return out

    def _apply_window_icon(self) -> None:
        """Set taskbar / Alt-Tab icon when the OS still shows one."""
        for path in self._icon_candidates():
            if not path.is_file():
                continue
            try:
                if path.suffix.lower() == ".ico":
                    self.root.iconbitmap(default=str(path))
                else:
                    self._wm_icon_image = tk.PhotoImage(file=str(path))
                    self.root.iconphoto(True, self._wm_icon_image)
                return
            except tk.TclError:
                continue

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        # Outer border frame (visual edge for borderless window)
        self.shell = tk.Frame(self.root, bg=BORDER, bd=0, highlightthickness=0)
        self.shell.pack(fill="both", expand=True, padx=0, pady=0)

        self.inner = tk.Frame(self.shell, bg=BG, bd=0, highlightthickness=0)
        self.inner.pack(fill="both", expand=True, padx=1, pady=1)

        # Thin drag strip only (no title text, no system buttons)
        grip = tk.Frame(self.inner, bg=BG_HEADER, height=18, cursor="fleur")
        grip.pack(fill="x", side="top")
        grip.pack_propagate(False)
        self._grip = grip

        grip_mark = tk.Label(
            grip,
            text="······",
            bg=BG_HEADER,
            fg=FG_MUTED,
            font=("Segoe UI", 7),
            cursor="fleur",
        )
        grip_mark.pack(side="left", expand=True)

        btn_style = dict(
            bg=BG_HEADER,
            fg=FG_MUTED,
            activebackground=BG_BLOCK,
            activeforeground=FG,
            relief="flat",
            bd=0,
            padx=6,
            cursor="hand2",
            font=("Microsoft YaHei UI", 9),
        )
        hide_btn = tk.Button(grip, text="–", command=self._hide_to_tray, **btn_style)
        hide_btn.pack(side="right", padx=(0, 2))
        hide_btn.configure(fg=FG_MUTED)

        pin_btn = tk.Button(grip, text="钉", command=self._toggle_topmost, **btn_style)
        pin_btn.pack(side="right")
        self._pin_btn = pin_btn

        # Drag bindings on grip (not on buttons)
        for w in (grip, grip_mark):
            w.bind("<ButtonPress-1>", self._start_move)
            w.bind("<B1-Motion>", self._do_move)
            w.bind("<ButtonRelease-1>", self._stop_move)

        # ---- bottom chrome first (status + composer) so it never disappears ----
        self.status = tk.Label(
            self.inner,
            text="左键复制 · 右键编辑 · 底部输入后点保存",
            bg=BG_PANEL,
            fg=FG_MUTED,
            font=("Microsoft YaHei UI", 8),
            anchor="w",
            padx=10,
            pady=4,
        )
        self.status.pack(fill="x", side="bottom")

        # Resize handle corner (bottom-right)
        resize_bar = tk.Frame(self.inner, bg=BG_PANEL, height=10)
        resize_bar.pack(fill="x", side="bottom")
        resize_bar.pack_propagate(False)
        corner = tk.Label(
            resize_bar,
            text="◢",
            bg=BG_PANEL,
            fg=FG_MUTED,
            font=("Segoe UI", 8),
            cursor="size_nw_se",
            padx=4,
        )
        corner.pack(side="right")
        corner.bind("<ButtonPress-1>", lambda e: self._start_resize(e, "se"))
        corner.bind("<B1-Motion>", self._do_resize)
        corner.bind("<ButtonRelease-1>", self._stop_resize)

        composer = tk.Frame(self.inner, bg=BG_PANEL, highlightthickness=0)
        composer.pack(fill="x", side="bottom", padx=0, pady=0)

        composer_label = tk.Label(
            composer,
            text="写笔记",
            bg=BG_PANEL,
            fg=FG_MUTED,
            font=("Microsoft YaHei UI", 8),
            anchor="w",
        )
        composer_label.pack(fill="x", padx=10, pady=(6, 0))

        input_row = tk.Frame(composer, bg=BG_PANEL)
        input_row.pack(fill="x", padx=8, pady=(4, 8))

        self.composer_text = tk.Text(
            input_row,
            height=2,
            wrap="word",
            bg=BG_BLOCK,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            font=("Microsoft YaHei UI", 9),
            padx=8,
            pady=4,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        self.composer_text.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.save_btn = tk.Button(
            input_row,
            text="保存",
            command=self.save_composer_note,
            bg=ACCENT,
            fg="#11111b",
            activebackground=ACCENT_DIM,
            activeforeground="#11111b",
            relief="flat",
            width=6,
            cursor="hand2",
            font=("Microsoft YaHei UI", 11, "bold"),
            padx=8,
            pady=10,
        )
        self.save_btn.pack(side="right", fill="y")

        # Scrollable note list (fills remaining space)
        body = tk.Frame(self.inner, bg=BG)
        body.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(body, bg=BG, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        self.list_frame = tk.Frame(self.canvas, bg=BG)

        self._list_window = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.list_frame.bind("<Configure>", self._on_list_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mousewheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Edge resize on whole window
        self.root.bind("<Motion>", self._on_motion_cursor)
        self.root.bind("<ButtonPress-1>", self._on_border_press, add="+")
        self.root.bind("<B1-Motion>", self._on_border_drag, add="+")
        self.root.bind("<ButtonRelease-1>", self._on_border_release, add="+")

    def _bind_events(self) -> None:
        self.root.bind("<Configure>", self._on_window_configure)
        self.root.bind("<Control-n>", lambda _e: self.add_note_dialog())
        self.root.bind("<Control-N>", lambda _e: self.add_note_dialog())
        self.root.bind("<Control-s>", lambda _e: self.save_composer_note())
        self.root.bind("<Control-S>", lambda _e: self.save_composer_note())
        self.composer_text.bind("<Control-Return>", lambda _e: self.save_composer_note())
        self.composer_text.bind("<Control-s>", lambda _e: self.save_composer_note())

    # ---------------------------------------------------------- move/resize
    def _start_move(self, event: tk.Event) -> None:
        self._drag_start = (event.x_root, event.y_root)
        self._win_start = (self.root.winfo_x(), self.root.winfo_y())

    def _do_move(self, event: tk.Event) -> None:
        if not self._drag_start:
            return
        dx = event.x_root - self._drag_start[0]
        dy = event.y_root - self._drag_start[1]
        x = self._win_start[0] + dx
        y = self._win_start[1] + dy
        self.root.geometry(f"+{x}+{y}")

    def _stop_move(self, _event: tk.Event | None = None) -> None:
        self._drag_start = None
        self._persist_geometry()

    def _hit_edge(self, x: int, y: int) -> str:
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        b = RESIZE_BORDER
        left = x < b
        right = x > w - b
        top = y < b
        bottom = y > h - b
        if top and left:
            return "nw"
        if top and right:
            return "ne"
        if bottom and left:
            return "sw"
        if bottom and right:
            return "se"
        if left:
            return "w"
        if right:
            return "e"
        if top:
            return "n"
        if bottom:
            return "s"
        return ""

    def _cursor_for_edge(self, edge: str) -> str:
        return {
            "n": "sb_v_double_arrow",
            "s": "sb_v_double_arrow",
            "e": "sb_h_double_arrow",
            "w": "sb_h_double_arrow",
            "nw": "size_nw_se",
            "se": "size_nw_se",
            "ne": "size_ne_sw",
            "sw": "size_ne_sw",
        }.get(edge, "")

    def _on_motion_cursor(self, event: tk.Event) -> None:
        if self._resize_edge or self._drag_start:
            return
        # Only change cursor near edges of root; ignore if over text inputs
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        if widget is not None and isinstance(widget, (tk.Text, tk.Entry, ttk.Entry)):
            return
        edge = self._hit_edge(event.x, event.y)
        cursor = self._cursor_for_edge(edge) or ""
        try:
            self.root.configure(cursor=cursor)
        except tk.TclError:
            pass

    def _on_border_press(self, event: tk.Event) -> None:
        if self._drag_start:
            return
        edge = self._hit_edge(event.x, event.y)
        if edge:
            self._start_resize(event, edge)

    def _on_border_drag(self, event: tk.Event) -> None:
        if self._resize_edge:
            self._do_resize(event)

    def _on_border_release(self, event: tk.Event) -> None:
        if self._resize_edge:
            self._stop_resize(event)

    def _start_resize(self, event: tk.Event, edge: str) -> None:
        self._resize_edge = edge
        self._resize_start = (
            event.x_root,
            event.y_root,
            self.root.winfo_x(),
            self.root.winfo_y(),
            self.root.winfo_width(),
            self.root.winfo_height(),
        )

    def _do_resize(self, event: tk.Event) -> None:
        if not self._resize_edge or not self._resize_start:
            return
        x0, y0, wx, wy, ww, wh = self._resize_start
        dx = event.x_root - x0
        dy = event.y_root - y0
        edge = self._resize_edge
        new_x, new_y, new_w, new_h = wx, wy, ww, wh

        if "e" in edge:
            new_w = max(self._min_w, ww + dx)
        if "s" in edge:
            new_h = max(self._min_h, wh + dy)
        if "w" in edge:
            new_w = max(self._min_w, ww - dx)
            new_x = wx + (ww - new_w)
        if "n" in edge:
            new_h = max(self._min_h, wh - dy)
            new_y = wy + (wh - new_h)

        self.root.geometry(f"{int(new_w)}x{int(new_h)}+{int(new_x)}+{int(new_y)}")

    def _stop_resize(self, _event: tk.Event | None = None) -> None:
        if self._resize_edge:
            self._resize_edge = None
            self._resize_start = None
            self._persist_geometry()

    def _on_list_configure(self, _event: tk.Event | None = None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._list_window, width=event.width)
        for block in self._blocks:
            block.set_wraplength(event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        if event.widget is self.root or str(event.widget).startswith(str(self.root)):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_window_configure(self, event: tk.Event) -> None:
        if event.widget is not self.root:
            return
        # Debounce persist of size/position so resize "sticks"
        if self._resize_save_after is not None:
            try:
                self.root.after_cancel(self._resize_save_after)
            except tk.TclError:
                pass
        self._resize_save_after = self.root.after(400, self._persist_geometry)

    def _persist_geometry(self) -> None:
        self._resize_save_after = None
        try:
            self.root.update_idletasks()
            self.config["width"] = self.root.winfo_width()
            self.config["height"] = self.root.winfo_height()
            self.config["x"] = self.root.winfo_x()
            self.config["y"] = self.root.winfo_y()
            storage.save_config(self.config)
        except tk.TclError:
            pass

    # --------------------------------------------------------------- notes
    def _render_notes(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()
        self._blocks.clear()

        max_chars = int(self.config.get("max_preview_chars") or 120)

        if not self.notes:
            empty = tk.Label(
                self.list_frame,
                text="暂无笔记\n在底部输入后点「保存」",
                bg=BG,
                fg=FG_MUTED,
                font=("Microsoft YaHei UI", 9),
                justify="center",
                pady=40,
            )
            empty.pack(fill="x", padx=12)
            return

        for note in self.notes:
            block = NoteBlock(
                self.list_frame,
                note=note,
                max_preview_chars=max_chars,
                on_copy=self.copy_note,
                on_edit=self.edit_note,
                on_delete=self.delete_note,
            )
            block.pack(fill="x", padx=10, pady=5)
            block.set_wraplength(self.canvas.winfo_width() or int(self.config.get("width") or 280))
            self._blocks.append(block)

    def _persist_notes(self) -> None:
        storage.save_notes(self.notes)

    def _add_note_text(self, text: str, toast: str = "已保存") -> None:
        text = text.strip()
        if not text:
            return
        note = {
            "id": storage.new_note_id(),
            "text": text,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        self.notes.insert(0, note)
        self._persist_notes()
        self._render_notes()
        self._show_toast(toast)

    def save_composer_note(self) -> str | None:
        """Save text from the always-visible bottom composer. Returns 'break' for key bindings."""
        try:
            text = self.composer_text.get("1.0", "end-1c").strip()
        except tk.TclError:
            return "break"
        if not text:
            self._show_toast("请先输入内容")
            return "break"
        self._add_note_text(text, toast="已保存")
        self.composer_text.delete("1.0", "end")
        return "break"

    def add_note_dialog(self) -> None:
        # Prefer focusing the on-window composer so Save is always visible
        try:
            self.composer_text.focus_set()
            self._show_toast("在底部输入，点右侧「保存」")
        except tk.TclError:
            pass

        def on_save(text: str) -> None:
            self._add_note_text(text, toast="已保存")

        dialog = NoteEditDialog(self.root, title="新建笔记", on_save=on_save)
        self.root.wait_window(dialog)

    def edit_note(self, note: dict[str, Any]) -> None:
        def on_save(text: str) -> None:
            note["text"] = text
            note["updated_at"] = _now_iso()
            self._persist_notes()
            self._render_notes()
            self._show_toast("已更新")

        dialog = NoteEditDialog(
            self.root,
            title="编辑笔记",
            initial=str(note.get("text", "")),
            on_save=on_save,
        )
        self.root.wait_window(dialog)

    def delete_note(self, note: dict[str, Any]) -> None:
        if not messagebox.askyesno(APP_TITLE, "确定删除这条笔记？", parent=self.root):
            return
        self.notes = [n for n in self.notes if n.get("id") != note.get("id")]
        self._persist_notes()
        self._render_notes()
        self._show_toast("已删除")

    def copy_note(self, note: dict[str, Any]) -> None:
        text = str(note.get("text", ""))
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()  # keep clipboard after window events
            self._show_toast("已复制到剪贴板")
        except tk.TclError:
            self._show_toast("复制失败")

    def _show_toast(self, message: str, ms: int = 1800) -> None:
        self.status.configure(text=message, fg=SUCCESS)
        if self._toast_after is not None:
            try:
                self.root.after_cancel(self._toast_after)
            except tk.TclError:
                pass

        def restore() -> None:
            self._toast_after = None
            try:
                self.status.configure(text="左键复制 · 右键编辑 · 底部输入后点保存", fg=FG_MUTED)
            except tk.TclError:
                pass

        self._toast_after = self.root.after(ms, restore)

    def _toggle_topmost(self) -> None:
        current = bool(self.config.get("always_on_top", True))
        new_val = not current
        self.config["always_on_top"] = new_val
        try:
            self.root.attributes("-topmost", new_val)
        except tk.TclError:
            pass
        storage.save_config(self.config)
        self._show_toast("已置顶" if new_val else "取消置顶")

    # --------------------------------------------------------------- tray
    def _start_tray(self) -> None:
        try:
            import pystray
            from PIL import Image, ImageDraw
        except ImportError:
            self._show_toast("托盘不可用（请安装 pystray Pillow）")
            return

        def make_icon() -> Any:
            # Prefer packaged / repo icon so tray matches exe icon
            for candidate in self._icon_candidates():
                if candidate.is_file():
                    try:
                        return Image.open(candidate).convert("RGBA")
                    except OSError:
                        pass
            size = 64
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle((4, 4, 60, 60), radius=12, fill=(137, 180, 250, 255))
            draw.rectangle((16, 20, 48, 26), fill=(17, 17, 27, 255))
            draw.rectangle((16, 32, 40, 38), fill=(17, 17, 27, 255))
            draw.rectangle((16, 44, 44, 50), fill=(17, 17, 27, 255))
            return img

        def on_show(icon: Any, _item: Any) -> None:
            self.root.after(0, self._show_window)

        def on_add(icon: Any, _item: Any) -> None:
            self.root.after(0, self.add_note_dialog)

        def on_toggle_autostart(icon: Any, _item: Any) -> None:
            enabled = is_autostart_enabled()
            ok = set_autostart(not enabled)
            if ok:
                self.config["autostart"] = not enabled
                storage.save_config(self.config)
                self.root.after(
                    0,
                    lambda: self._show_toast("已开启自启动" if not enabled else "已关闭自启动"),
                )
                try:
                    icon.update_menu()
                except Exception:
                    pass

        def on_quit(icon: Any, _item: Any) -> None:
            self.root.after(0, lambda: self.quit_app(icon))

        def autostart_text(_item: Any) -> str:
            return "关闭开机自启" if is_autostart_enabled() else "开启开机自启"

        menu = pystray.Menu(
            pystray.MenuItem("显示窗口", on_show, default=True),
            pystray.MenuItem("添加笔记", on_add),
            pystray.MenuItem(autostart_text, on_toggle_autostart),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", on_quit),
        )

        self._tray = pystray.Icon(APP_TITLE, make_icon(), APP_TITLE, menu)

        def run_tray() -> None:
            try:
                self._tray.run()
            except Exception:
                pass

        self._tray_thread = threading.Thread(target=run_tray, daemon=True)
        self._tray_thread.start()

    def _show_window(self) -> None:
        try:
            # overrideredirect windows need explicit restore
            self.root.overrideredirect(True)
            self.root.deiconify()
            self.root.lift()
            if self.config.get("always_on_top", True):
                self.root.attributes("-topmost", True)
            try:
                opacity = float(self.config.get("opacity", 0.92))
                self.root.attributes("-alpha", max(0.5, min(1.0, opacity)))
            except (TypeError, ValueError, tk.TclError):
                pass
            self.root.focus_force()
        except tk.TclError:
            pass

    def _hide_to_tray(self) -> None:
        self._persist_geometry()
        try:
            self.root.withdraw()
        except tk.TclError:
            pass

    def _on_close_window(self) -> None:
        # Close button hides to tray; quit only from tray menu
        self._hide_to_tray()

    def quit_app(self, tray_icon: Any = None) -> None:
        if self._closing:
            return
        self._closing = True
        self._persist_geometry()
        self._persist_notes()
        _clear_pid()
        icon = tray_icon or self._tray
        if icon is not None:
            try:
                icon.stop()
            except Exception:
                pass
        try:
            self.root.quit()
            self.root.destroy()
        except tk.TclError:
            pass

    def run(self) -> None:
        self.root.mainloop()
        _clear_pid()


def _already_running() -> bool:
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return False
    # Check if process exists (Windows)
    try:
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
    except Exception:
        pass
    return False


def main() -> None:
    if sys.platform == "win32" and _already_running():
        # Second instance: exit quietly (primary keeps floating)
        return
    app = FloatingNoteApp()
    app.run()


if __name__ == "__main__":
    main()
