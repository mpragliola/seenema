import threading
import pystray
from PIL import Image
from src.config import AppState, save_config
from src.monitor import MonitorInfo
from src.autostart import enable_autostart, disable_autostart
from src.overlay import OverlayManager

_OPACITY_STEPS = [i / 100 for i in range(10, 110, 10)]


def _load_icon_image(path: str) -> Image.Image:
    try:
        return Image.open(path)
    except Exception:
        img = Image.new('RGB', (64, 64), color=(26, 26, 46))
        return img


class TrayApp:
    def __init__(
        self,
        state: AppState,
        overlay: OverlayManager,
        monitors: list[MonitorInfo],
        icon_path: str,
        on_quit: callable,
        schedule: callable,
    ):
        self._state = state
        self._overlay = overlay
        self._monitors = monitors
        self._on_quit = on_quit
        self._schedule = schedule  # schedule(fn) -> runs fn on main (tkinter) thread
        self._image = _load_icon_image(icon_path)
        self._icon = pystray.Icon(
            'seenema',
            self._image,
            'Seenema',
            menu=self._build_menu(),
        )

    def update_monitors(self, monitors: list[MonitorInfo]) -> None:
        # Called from the main thread (poll_monitors via root.after)
        self._monitors = monitors
        self._icon.menu = self._build_menu()
        self._icon.update_menu()

    def _refresh_menu(self) -> None:
        self._icon.menu = self._build_menu()
        self._icon.update_menu()

    def _build_menu(self) -> pystray.Menu:
        can_dim = (
            self._state.main_display is not None
            and len(self._monitors) > 1
        )

        dim_label = 'Dim: ON' if self._state.dim_enabled else 'Dim: OFF'

        display_items = [
            pystray.MenuItem(
                m.name,
                self._make_set_display(m.name),
                checked=lambda item, n=m.name: self._state.main_display == n,
                radio=True,
            )
            for m in self._monitors
        ]

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

    def _make_set_display(self, name: str):
        def handler(icon, item):
            self._state.main_display = name
            save_config(self._state)
            monitors = self._monitors
            def do():
                self._overlay.rebuild(monitors, name)
            self._schedule(do)
            self._refresh_menu()
        return handler

    def _make_set_opacity(self, value: float):
        def handler(icon, item):
            self._state.opacity = value
            save_config(self._state)
            def do():
                self._overlay.set_opacity(value)
            self._schedule(do)
            self._refresh_menu()
        return handler

    def _toggle_dim(self, icon, item):
        if self._state.dim_enabled:
            self._state.dim_enabled = False
            def do():
                self._overlay.hide()
        else:
            self._state.dim_enabled = True
            opacity = self._state.opacity
            def do():
                self._overlay.show(opacity)
        self._schedule(do)
        self._refresh_menu()

    def _toggle_autostart(self, icon, item):
        self._state.autostart = not self._state.autostart
        if self._state.autostart:
            enable_autostart()
        else:
            disable_autostart()
        save_config(self._state)
        self._refresh_menu()

    def _quit(self, icon, item):
        self._icon.stop()
        self._on_quit()

    def run(self) -> None:
        thread = threading.Thread(target=self._icon.run, daemon=True)
        thread.start()
