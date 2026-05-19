import json
import os
from dataclasses import dataclass, asdict


@dataclass
class AppState:
    main_display: str | None = None
    opacity: float = 0.90
    autostart: bool = False
    dim_enabled: bool = False


def _get_default_config_path() -> str:
    import sys
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'config.json')


def load_config(path: str | None = None) -> AppState:
    if path is None:
        path = _get_default_config_path()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        opacity = float(data.get('opacity', 0.90))
        opacity = max(0.10, min(1.0, opacity))
        return AppState(
            main_display=data.get('main_display'),
            opacity=opacity,
            autostart=bool(data.get('autostart', False)),
            dim_enabled=False,  # never restore dim state on launch
        )
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return AppState()


def save_config(state: AppState, path: str | None = None) -> None:
    if path is None:
        path = _get_default_config_path()
    data = asdict(state)
    data.pop('dim_enabled', None)  # never persist runtime-only state
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
