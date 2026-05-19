from dataclasses import dataclass
import screeninfo


@dataclass(frozen=True)
class MonitorInfo:
    name: str
    x: int
    y: int
    width: int
    height: int


def get_monitors() -> list[MonitorInfo]:
    try:
        raw = screeninfo.get_monitors()
        return [
            MonitorInfo(
                name=m.name,
                x=m.x,
                y=m.y,
                width=m.width,
                height=m.height,
            )
            for m in raw
        ]
    except Exception:
        return []


def monitors_changed(prev: list[MonitorInfo], curr: list[MonitorInfo]) -> bool:
    return prev != curr
