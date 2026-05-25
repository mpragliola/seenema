# overlay.py — Creates and manages full-screen black overlay windows on secondary monitors.
#
# The overlay is a borderless, always-on-top, click-through tkinter window. "Click-through"
# is achieved via Win32 extended window styles: the OS routes mouse/keyboard input to whatever
# is beneath the overlay, so the user can interact with content on other monitors normally.
#
# Architecture:
#   _OverlayWindow    — wraps a single tk.Toplevel for one physical monitor
#   OverlayManager    — owns all _OverlayWindow instances; recreated whenever the monitor
#                       layout changes; exposes show/hide/opacity to the rest of the app

import ctypes
import tkinter as tk
from src.config import DIM_ALL_MIN_OPACITY
from src.monitor import MonitorInfo

# Win32 constants for GetWindowLongW / SetWindowLongW
GWL_EXSTYLE = -20           # index: extended window style register
WS_EX_LAYERED = 0x80000     # required for per-pixel alpha and colour-key transparency
WS_EX_TRANSPARENT = 0x20    # makes the window pass all mouse input to the window below it
WS_EX_TOOLWINDOW = 0x80     # hides the window from the taskbar and Alt-Tab list
WS_EX_NOACTIVATE = 0x08000000  # prevents the window from stealing keyboard focus on show

# GetAncestor flag: walk the parent chain and return the root (top-level) window
GA_ROOT = 2


def _top_level_hwnd(child_hwnd: int) -> int:
    # tkinter's winfo_id() can return a child HWND (e.g. the canvas inside the Toplevel);
    # extended styles such as WS_EX_TRANSPARENT only work when applied to the outermost
    # top-level HWND, so we must walk up the ancestor chain first.
    root = ctypes.windll.user32.GetAncestor(child_hwnd, GA_ROOT)
    # GetAncestor returns NULL if hwnd is already a top-level window with no parent;
    # fall back to the original handle in that case so the caller always gets a valid HWND.
    return root or child_hwnd


def _apply_click_through(hwnd: int) -> None:
    # Fetch the top-level HWND because styles on child windows are silently ignored.
    hwnd = _top_level_hwnd(hwnd)

    # Read the current extended style bits so we don't accidentally clear unrelated flags.
    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)

    # OR in the four flags that together make the window:
    #   • visible but non-interactive (LAYERED + TRANSPARENT)
    #   • absent from taskbar / Alt-Tab (TOOLWINDOW)
    #   • unable to steal focus (NOACTIVATE)
    new_style = style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)


class _OverlayWindow:
    """A borderless, click-through, always-on-top black window covering one monitor."""

    def __init__(self, root: tk.Tk, monitor: MonitorInfo):
        self._monitor = monitor

        # Use a Toplevel so we can have one window per monitor while sharing the same
        # Tk event loop driven by `root`.
        self._win = tk.Toplevel(root)

        # overrideredirect(True) removes the OS title bar and window chrome entirely,
        # giving us a plain frameless surface that can fill the monitor edge-to-edge.
        self._win.overrideredirect(True)

        # Keep the overlay in front of all other application windows at all times.
        self._win.attributes('-topmost', True)

        # Initial alpha; callers may override this via show(opacity=...) later.
        self._win.attributes('-alpha', 0.90)

        # Black fill — the visual purpose of the overlay is to dim secondary monitors.
        self._win.configure(bg='black')

        # Position and size the window to exactly cover the physical monitor rect.
        # The geometry string format is  WxH+X+Y  (pixels, origin = top-left of monitor).
        self._win.geometry(
            f"{monitor.width}x{monitor.height}+{monitor.x}+{monitor.y}"
        )

        # Force geometry to be committed before we query the HWND; without this the
        # window may not have a real OS handle yet and winfo_id() could be unreliable.
        self._win.update_idletasks()

        # Apply click-through styles immediately after the OS window is created.
        _apply_click_through(self._win.winfo_id())

        # Start hidden; the caller decides when to make the overlay visible.
        self._win.withdraw()

    def show(self, opacity: float) -> None:
        """Make the overlay visible with the given opacity (0.0 – 1.0)."""
        self._win.attributes('-alpha', opacity)

        # deiconify() reverses withdraw(), making the window visible again.
        self._win.deiconify()

        # Raise above any window that may have appeared on top since we last showed.
        self._win.lift()

        # Commit the pending geometry/attribute changes to the OS before proceeding.
        self._win.update_idletasks()

        # Re-apply click-through: on some Windows versions deiconify() or lift() resets
        # the extended window styles, which would make the overlay capture mouse clicks.
        _apply_click_through(self._win.winfo_id())

    def hide(self) -> None:
        """Remove the overlay from the screen without destroying it."""
        self._win.withdraw()

    def set_opacity(self, opacity: float) -> None:
        """Adjust transparency while the overlay is already visible."""
        self._win.attributes('-alpha', opacity)

    def destroy(self) -> None:
        """Permanently destroy the underlying OS window and free its resources."""
        self._win.destroy()

    @property
    def monitor_name(self) -> str:
        """The canonical name of the physical monitor this window covers (e.g. '\\\\.\\DISPLAY2')."""
        return self._monitor.name


class OverlayManager:
    """Owns all per-monitor overlay windows and exposes a unified show/hide/opacity API.

    Call `rebuild()` whenever the monitor layout changes (monitors added, removed, or the
    main display selection changes).  The manager tracks visibility and opacity across
    rebuilds so callers don't need to re-issue show() after a rebuild.
    """

    def __init__(self, root: tk.Tk):
        # The shared Tk root — passed through to each _OverlayWindow so they all share
        # one event loop instead of creating independent Tk instances.
        self._root = root

        # Live overlay windows; one entry per secondary monitor currently in use.
        self._windows: list[_OverlayWindow] = []

        # Tracks whether the overlay is logically "on" so rebuild() can restore state.
        self._visible = False

        # Last-requested opacity; preserved across rebuild() and show() calls without
        # an explicit opacity argument.
        self._opacity = 0.90

        # True when rebuild_all() is active (every monitor covered).
        self._dim_all = False

    def rebuild(self, monitors: list[MonitorInfo], main_display: str | None) -> None:
        """Destroy existing overlay windows and create fresh ones for the current monitor layout.

        `main_display` is the monitor name that should remain uncovered (the user's primary
        working screen).  All other monitors in `monitors` get an overlay window.

        If the overlay was visible before the rebuild it is automatically re-shown on the
        new windows so the dimming effect is uninterrupted from the user's perspective.
        """
        # Clean up every existing OS window before recreating; avoids ghost windows if
        # a monitor was unplugged or if main_display changed.
        for w in self._windows:
            w.destroy()

        self._dim_all = False

        # Create one overlay per non-main monitor.
        self._windows = [
            _OverlayWindow(self._root, m)
            for m in monitors
            if m.name != main_display
        ]

        # Restore visibility on the new windows so the caller doesn't need to call show()
        # again after every monitor-layout change.
        if self._visible:
            for w in self._windows:
                w.show(self._opacity)

    def rebuild_all(self, monitors: list[MonitorInfo]) -> None:
        """Destroy existing windows and create an overlay on every monitor."""
        for w in self._windows:
            w.destroy()
        self._dim_all = True
        self._windows = [_OverlayWindow(self._root, m) for m in monitors]
        if self._visible:
            for w in self._windows:
                w.show(self._opacity)

    def show(self, opacity: float | None = None) -> None:
        """Show the overlay on all secondary monitors.

        If `opacity` is provided it becomes the new stored opacity; otherwise the
        previously stored value is reused.
        """
        if opacity is not None:
            self._opacity = opacity
        self._visible = True
        for w in self._windows:
            w.show(self._opacity)

    def hide(self) -> None:
        """Hide the overlay from all secondary monitors without destroying the windows."""
        self._visible = False
        for w in self._windows:
            w.hide()

    def set_opacity(self, opacity: float) -> None:
        """Update opacity on all visible overlay windows and store it for future shows."""
        self._opacity = opacity
        # Only push the change to the OS if the windows are currently on screen;
        # if hidden, the stored value will be used the next time show() is called.
        if self._visible:
            for w in self._windows:
                w.set_opacity(opacity)

    def set_mouse_monitor(self, name: str | None) -> None:
        """Apply DIM_ALL_MIN_OPACITY floor to the monitor under the cursor.

        All other monitors get the bare stored opacity. No-op when hidden.
        """
        if not self._visible:
            return
        for w in self._windows:
            if w.monitor_name == name:
                w.set_opacity(max(self._opacity, DIM_ALL_MIN_OPACITY))
            else:
                w.set_opacity(self._opacity)

    @property
    def is_visible(self) -> bool:
        """True if the overlay is currently shown on screen."""
        return self._visible

    @property
    def dim_all(self) -> bool:
        """True if every monitor is covered (no main display exclusion)."""
        return self._dim_all
