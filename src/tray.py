# tray.py — System-tray icon and menu for Seenema.
#
# pystray runs its event loop on a dedicated background thread (started in TrayApp.run()).
# All menu callbacks therefore execute on that thread, NOT on the tkinter main thread.
# Any operation that touches tkinter widgets (overlays, geometry, etc.) must be
# marshalled back to the main thread via self._schedule(fn), which wraps root.after().
#
# Menu structure:
#   Dim: ON / OFF          — toggle overlay visibility
#   ─────────────────
#   Main display >         — radio group: which monitor to leave uncovered
#   ─────────────────
#   Opacity >              — radio group: 5 % … 100 % in 5 % steps
#   ─────────────────
#   Start with Windows     — checkbox: Windows Run-key autostart
#   ─────────────────
#   Quit

import threading
from collections.abc import Callable
import pystray
from PIL import Image
from src.config import AppState, save_config
from src.monitor import MonitorInfo
from src.autostart import enable_autostart, disable_autostart
from src.overlay import OverlayManager

# Pre-computed opacity levels: [0.05, 0.10, …, 1.00]
# Using integer arithmetic to avoid floating-point drift (e.g. 0.30000000000000004).
_OPACITY_STEPS = [i / 100 for i in range(5, 105, 5)]


def _load_icon_image(path: str) -> Image.Image:
    """Load the tray icon from `path`, falling back to a plain dark square on error.

    The fallback prevents the app from crashing when the icon file is missing or
    unreadable — the tray icon will just look like a coloured square instead.
    """
    try:
        return Image.open(path)
    except Exception:
        # 64 × 64 dark-blue square as a minimal visible placeholder.
        img = Image.new('RGB', (64, 64), color=(26, 26, 46))
        return img


class TrayApp:
    """Manages the system-tray icon, menu state, and user interactions.

    The tray icon runs on a background thread; all tkinter operations are
    dispatched to the main thread through `schedule`.

    Args:
        state       — shared AppState; mutated in-place on menu interactions
        overlay     — OverlayManager that controls the per-monitor dim windows
        monitors    — current monitor list; updated via update_monitors()
        icon_path   — path to the .ico / .png file for the tray icon
        on_quit     — called (on the tray thread) when the user clicks Quit
        schedule    — callable that queues a zero-argument function onto the
                      tkinter main thread (i.e. wraps root.after)
    """

    def __init__(
        self,
        state: AppState,
        overlay: OverlayManager,
        monitors: list[MonitorInfo],
        icon_path: str,
        on_quit: Callable,
        schedule: Callable,
    ):
        self._state = state
        self._overlay = overlay
        self._monitors = monitors
        self._on_quit = on_quit
        self._schedule = schedule  # schedule(fn) → runs fn on the tkinter main thread
        self._image = _load_icon_image(icon_path)

        # Create the pystray icon but do NOT start it yet — run() does that.
        self._icon = pystray.Icon(
            'seenema',
            self._image,
            'Seenema',
            menu=self._build_menu(),
        )

    def update_monitors(self, monitors: list[MonitorInfo]) -> None:
        """Refresh the monitor list and rebuild the tray menu to reflect the new layout.

        Called from the main thread (via root.after) whenever poll_monitors detects a
        change so the "Main display" submenu stays in sync with connected monitors.
        """
        self._monitors = monitors
        self._icon.menu = self._build_menu()
        self._icon.update_menu()

    def _refresh_menu(self) -> None:
        # Rebuild and push the menu to pystray after any state mutation.
        # Called from the tray thread, so it must not touch tkinter directly.
        self._icon.menu = self._build_menu()
        self._icon.update_menu()

    def _build_menu(self) -> pystray.Menu:
        can_dim = (
            self._state.dim_all
            or (self._state.main_display is not None and len(self._monitors) > 1)
        )

        dim_label = 'Dim: ON' if self._state.dim_enabled else 'Dim: OFF'

        all_screens_item = pystray.MenuItem(
            'All screens',
            self._set_all_screens,
            checked=lambda item: self._state.dim_all,
            radio=True,
        )

        # One radio item per connected monitor; the checked item reflects AppState.main_display.
        # The `n=m.name` default-argument capture is required because Python closures
        # capture variables by reference — without it all lambdas would share the last `m`.
        display_items = [all_screens_item] + [
            pystray.MenuItem(
                m.name,
                self._make_set_display(m.name),
                checked=lambda item, n=m.name: (not self._state.dim_all) and self._state.main_display == n,
                radio=True,
            )
            for m in self._monitors
        ]

        # One radio item per opacity step; the checked item is within 1 % of the stored value.
        # The `v=v` capture is the same closure-capture guard as above.
        opacity_items = [
            pystray.MenuItem(
                f'{int(round(v * 100))}%',
                self._make_set_opacity(v),
                checked=lambda item, v=v: abs(self._state.opacity - v) < 0.01,
                radio=True,
            )
            for v in _OPACITY_STEPS
        ]

        return pystray.Menu(
            pystray.MenuItem(
                dim_label,
                self._toggle_dim,
                enabled=can_dim,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Main display', pystray.Menu(*display_items)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Opacity', pystray.Menu(*opacity_items)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                'Start with Windows',
                self._toggle_autostart,
                checked=lambda item: self._state.autostart,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Quit', self._quit),
        )

    def _set_all_screens(self, icon, item):
        """Select 'All screens' mode: dim every monitor with live mouse-position clamping."""
        self._state.dim_all = True
        self._state.main_display = None
        save_config(self._state)

        monitors = self._monitors

        def do():
            self._overlay.rebuild_all(monitors)
            if self._state.dim_enabled:
                self._overlay.show(self._state.opacity)
                start_poll = getattr(self._state, '_start_mouse_poll', None)
                if start_poll:
                    start_poll()

        self._schedule(do)
        self._refresh_menu()

    def _make_set_display(self, name: str):
        """Return a menu callback that sets `name` as the main (uncovered) display.

        Creating the handler via a factory function rather than a lambda ensures `name`
        is bound at definition time, not at call time (the classic loop-closure pitfall).
        """
        def handler(icon, item):
            self._state.dim_all = False
            self._state.main_display = name
            save_config(self._state)

            # Capture the current monitor list before crossing thread boundaries;
            # self._monitors could be replaced by update_monitors() on the main thread
            # between now and when `do` executes.
            monitors = self._monitors

            def do():
                # Must run on the main thread because OverlayManager touches tkinter.
                self._overlay.rebuild(monitors, name)

            self._schedule(do)
            self._refresh_menu()
        return handler

    def _make_set_opacity(self, value: float):
        """Return a menu callback that applies `value` as the new overlay opacity."""
        def handler(icon, item):
            self._state.opacity = value
            save_config(self._state)

            def do():
                # Must run on the main thread — OverlayManager calls tkinter attributes.
                self._overlay.set_opacity(value)

            self._schedule(do)
            self._refresh_menu()
        return handler

    def _toggle_dim(self, icon, item):
        """Show or hide the overlay on all secondary monitors."""
        if self._state.dim_enabled:
            self._state.dim_enabled = False
            def do():
                self._overlay.hide()
        else:
            self._state.dim_enabled = True
            # Capture opacity now; the user could change it before `do` runs.
            opacity = self._state.opacity
            def do():
                self._overlay.show(opacity)
                if self._state.dim_all:
                    start_poll = getattr(self._state, '_start_mouse_poll', None)
                    if start_poll:
                        start_poll()

        # dim_enabled is intentionally not saved to disk — see config.py.
        self._schedule(do)
        self._refresh_menu()

    def _toggle_autostart(self, icon, item):
        """Register or deregister the app in the Windows Run key."""
        self._state.autostart = not self._state.autostart
        if self._state.autostart:
            enable_autostart()
        else:
            disable_autostart()
        save_config(self._state)
        self._refresh_menu()

    def _quit(self, icon, item):
        # Stop the pystray icon loop first, then notify the main thread to clean up.
        self._icon.stop()
        self._on_quit()

    def run(self) -> None:
        """Start the pystray event loop on a daemon thread.

        The thread is a daemon so it does not prevent the process from exiting if the
        main thread finishes (e.g. after an unhandled exception in the tkinter loop).
        """
        thread = threading.Thread(target=self._icon.run, daemon=True)
        thread.start()
