import os
import sys
import tkinter as tk

from src.config import load_config, save_config
from src.monitor import get_monitors, monitors_changed
from src.overlay import OverlayManager
from src.tray import TrayApp

POLL_INTERVAL_MS = 5000


def _get_icon_path() -> str:
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'assets', 'icon.ico')


def main():
    state = load_config()
    monitors = get_monitors()

    root = tk.Tk()
    root.withdraw()

    overlay = OverlayManager(root)
    overlay.rebuild(monitors, state.main_display)

    def on_quit():
        root.after(0, root.quit)

    tray = TrayApp(
        state=state,
        overlay=overlay,
        monitors=monitors,
        icon_path=_get_icon_path(),
        on_quit=on_quit,
        schedule=lambda fn: root.after(0, fn),
    )
    tray.run()

    def poll_monitors():
        nonlocal monitors
        current = get_monitors()
        if monitors_changed(monitors, current):
            monitors = current
            # If saved main display is gone, disable dim
            names = {m.name for m in current}
            if state.main_display not in names:
                state.main_display = None
                state.dim_enabled = False
                overlay.hide()
                save_config(state)
            overlay.rebuild(current, state.main_display)
            tray.update_monitors(current)
        root.after(POLL_INTERVAL_MS, poll_monitors)

    root.after(POLL_INTERVAL_MS, poll_monitors)
    root.mainloop()


if __name__ == '__main__':
    main()
