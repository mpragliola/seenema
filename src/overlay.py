import ctypes
import tkinter as tk
from src.monitor import MonitorInfo

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20


def _apply_click_through(hwnd: int) -> None:
    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(
        hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT
    )


class _OverlayWindow:
    def __init__(self, root: tk.Tk, monitor: MonitorInfo):
        self._monitor = monitor
        self._win = tk.Toplevel(root)
        self._win.overrideredirect(True)
        self._win.attributes('-topmost', True)
        self._win.attributes('-alpha', 0.90)
        self._win.configure(bg='black')
        self._win.geometry(
            f"{monitor.width}x{monitor.height}+{monitor.x}+{monitor.y}"
        )
        self._win.update()
        _apply_click_through(self._win.winfo_id())
        self._win.withdraw()

    def show(self, opacity: float) -> None:
        self._win.attributes('-alpha', opacity)
        self._win.deiconify()
        self._win.lift()

    def hide(self) -> None:
        self._win.withdraw()

    def set_opacity(self, opacity: float) -> None:
        self._win.attributes('-alpha', opacity)

    def destroy(self) -> None:
        self._win.destroy()

    @property
    def monitor_name(self) -> str:
        return self._monitor.name


class OverlayManager:
    def __init__(self, root: tk.Tk):
        self._root = root
        self._windows: list[_OverlayWindow] = []
        self._visible = False
        self._opacity = 0.90

    def rebuild(self, monitors: list[MonitorInfo], main_display: str | None) -> None:
        for w in self._windows:
            w.destroy()
        self._windows = [
            _OverlayWindow(self._root, m)
            for m in monitors
            if m.name != main_display
        ]
        if self._visible:
            for w in self._windows:
                w.show(self._opacity)

    def show(self, opacity: float | None = None) -> None:
        if opacity is not None:
            self._opacity = opacity
        self._visible = True
        for w in self._windows:
            w.show(self._opacity)

    def hide(self) -> None:
        self._visible = False
        for w in self._windows:
            w.hide()

    def set_opacity(self, opacity: float) -> None:
        self._opacity = opacity
        if self._visible:
            for w in self._windows:
                w.set_opacity(opacity)

    @property
    def is_visible(self) -> bool:
        return self._visible
