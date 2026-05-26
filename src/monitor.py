# monitor.py — Thin wrapper around screeninfo for querying physical monitor geometry.
#
# MonitorInfo is an immutable snapshot of one monitor's position and size in the
# virtual desktop coordinate space.  The rest of the app uses these snapshots to:
#   • position overlay windows (overlay.py)
#   • detect layout changes that require a rebuild (main loop)
#   • populate the "Main display" submenu (tray.py)
#
# Using a frozen dataclass means two MonitorInfo lists can be compared with == to
# detect layout changes without writing a custom equality function (see monitors_changed).

from dataclasses import dataclass
import screeninfo


@dataclass(frozen=True)
class MonitorInfo:
    """Immutable geometry snapshot for a single physical monitor.

    Coordinates are in the virtual desktop space where (0, 0) is the top-left corner
    of the primary monitor.  Secondary monitors may have negative x/y values if they
    are positioned to the left of or above the primary.

    Attributes:
        name    — OS-assigned identifier, e.g. '\\\\.\\DISPLAY1' on Windows
        x, y    — top-left corner of the monitor in virtual desktop coordinates
        width   — horizontal resolution in pixels
        height  — vertical resolution in pixels
    """
    name: str
    x: int
    y: int
    width: int
    height: int


def get_monitors() -> list[MonitorInfo]:
    """Return a snapshot of all currently connected monitors.

    Returns an empty list if screeninfo raises (e.g. no display server, headless CI).
    Callers should treat an empty list as "layout unknown" rather than "no monitors".
    """
    try:
        raw = screeninfo.get_monitors()
        return [
            MonitorInfo(
                name=m.name or "",
                x=m.x,
                y=m.y,
                width=m.width,
                height=m.height,
            )
            for m in raw
        ]
    except Exception:
        # screeninfo can raise on unexpected display configurations; never crash the app.
        return []


def monitors_changed(prev: list[MonitorInfo], curr: list[MonitorInfo]) -> bool:
    """Return True if the monitor layout has changed between two snapshots.

    Because MonitorInfo is a frozen dataclass, list equality performs a deep structural
    comparison — order, count, and every field must match for the lists to be equal.
    A monitor being unplugged, added, or moved will therefore correctly return True.
    """
    return prev != curr
