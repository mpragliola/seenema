from unittest.mock import patch, MagicMock
from src.monitor import MonitorInfo, get_monitors, monitors_changed


def _make_screeninfo_monitor(name, x, y, width, height):
    m = MagicMock()
    m.name = name
    m.x = x
    m.y = y
    m.width = width
    m.height = height
    return m


def test_get_monitors_returns_monitor_info_list():
    fake = [
        _make_screeninfo_monitor(r"\\.\DISPLAY1", 0, 0, 1920, 1080),
        _make_screeninfo_monitor(r"\\.\DISPLAY2", 1920, 0, 2560, 1440),
    ]
    with patch('src.monitor.screeninfo.get_monitors', return_value=fake):
        result = get_monitors()
    assert len(result) == 2
    assert isinstance(result[0], MonitorInfo)
    assert result[0].name == r"\\.\DISPLAY1"
    assert result[0].x == 0
    assert result[0].width == 1920
    assert result[1].name == r"\\.\DISPLAY2"
    assert result[1].x == 1920


def test_get_monitors_returns_empty_on_error():
    with patch('src.monitor.screeninfo.get_monitors', side_effect=Exception("fail")):
        result = get_monitors()
    assert result == []


def test_monitors_changed_detects_added():
    prev = [MonitorInfo(r"\\.\DISPLAY1", 0, 0, 1920, 1080)]
    curr = [
        MonitorInfo(r"\\.\DISPLAY1", 0, 0, 1920, 1080),
        MonitorInfo(r"\\.\DISPLAY2", 1920, 0, 2560, 1440),
    ]
    assert monitors_changed(prev, curr) is True


def test_monitors_changed_detects_removed():
    prev = [
        MonitorInfo(r"\\.\DISPLAY1", 0, 0, 1920, 1080),
        MonitorInfo(r"\\.\DISPLAY2", 1920, 0, 2560, 1440),
    ]
    curr = [MonitorInfo(r"\\.\DISPLAY1", 0, 0, 1920, 1080)]
    assert monitors_changed(prev, curr) is True


def test_monitors_changed_no_change():
    monitors = [MonitorInfo(r"\\.\DISPLAY1", 0, 0, 1920, 1080)]
    assert monitors_changed(monitors, monitors) is False


def test_monitors_changed_detects_resolution_change():
    prev = [MonitorInfo(r"\\.\DISPLAY1", 0, 0, 1920, 1080)]
    curr = [MonitorInfo(r"\\.\DISPLAY1", 0, 0, 2560, 1440)]
    assert monitors_changed(prev, curr) is True
