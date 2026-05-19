# config.py — Persistent application state: load from / save to config.json.
#
# AppState is the single source of truth for all user-configurable settings.
# It is loaded once at startup, mutated in-place as the user interacts with the tray
# menu, and written back to disk after each change.
#
# config.json lives next to the executable when frozen (PyInstaller) or at the
# project root when running from source.  This keeps the config portable — the user
# can carry the exe + config.json together without registry entries.

import json
import os
from dataclasses import dataclass, asdict


@dataclass
class AppState:
    """All user-configurable settings, plus transient runtime flags.

    Fields persisted to config.json:
        main_display  — name of the monitor that should NOT be dimmed (e.g. '\\\\.\\DISPLAY1')
        opacity       — overlay opacity in [0.10, 1.0]; 0.90 by default
        autostart     — whether the app registers itself in the Windows Run key

    Runtime-only fields (never written to disk):
        dim_enabled   — whether the overlay is currently shown; always starts False so
                        the user has an explicit choice each session
    """
    main_display: str | None = None
    opacity: float = 0.90
    autostart: bool = False
    dim_enabled: bool = False   # intentionally not persisted — see save_config()


def _get_default_config_path() -> str:
    # Delay-import sys here so this module can be imported without triggering
    # PyInstaller's sys.frozen detection at module load time.
    import sys

    if getattr(sys, 'frozen', False):
        # PyInstaller bundles the app into a single exe; sys.executable is that exe.
        # Place config.json next to it so it travels with the binary.
        base = os.path.dirname(sys.executable)
    else:
        # Running from source: __file__ is src/config.py, so go up two levels to reach
        # the project root where config.json is expected.
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base, 'config.json')


def load_config(path: str | None = None) -> AppState:
    """Read config.json and return a populated AppState.

    Falls back to a default AppState (all fields at their default values) if the
    file is missing, malformed, or contains an invalid opacity value.  This means
    the app always starts in a safe state even on first run.

    `path` is optional; when omitted the platform-appropriate default path is used.
    """
    if path is None:
        path = _get_default_config_path()

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Clamp opacity to a usable range: fully transparent (0.0) would make the
        # overlay invisible and confusing; values above 1.0 are rejected by tkinter.
        opacity = float(data.get('opacity', 0.90))
        opacity = max(0.10, min(1.0, opacity))

        return AppState(
            main_display=data.get('main_display'),
            opacity=opacity,
            autostart=bool(data.get('autostart', False)),
            # Never restore dim_enabled from disk — the user always starts with
            # dimming off and activates it manually via the tray menu.
            dim_enabled=False,
        )
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        # Missing file → first run; bad JSON → corrupted config.  Either way,
        # return defaults rather than crashing so the app is always launchable.
        return AppState()


def save_config(state: AppState, path: str | None = None) -> None:
    """Serialize AppState to config.json, omitting runtime-only fields.

    `dim_enabled` is deliberately excluded: it represents transient UI state
    (is the overlay currently on?) which should reset to False on every launch.

    `path` is optional; when omitted the platform-appropriate default path is used.
    """
    if path is None:
        path = _get_default_config_path()

    # asdict() converts the dataclass to a plain dict for JSON serialisation.
    data = asdict(state)

    # Strip the runtime-only flag before writing so it never reaches disk.
    data.pop('dim_enabled', None)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
