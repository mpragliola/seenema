import sys
import types
import ctypes
from unittest.mock import MagicMock

# Minimal tkinter stub so overlay.py can be imported without a display
tk_stub = types.ModuleType('tkinter')

class _FakeTk:
    def withdraw(self): pass

class _FakeToplevel:
    def __init__(self, *a, **kw): pass
    def overrideredirect(self, v): pass
    def attributes(self, *a): pass
    def configure(self, **kw): pass
    def geometry(self, s): pass
    def update_idletasks(self): pass
    def withdraw(self): pass
    def deiconify(self): pass
    def lift(self): pass
    def destroy(self): pass
    def winfo_id(self): return 1

tk_stub.Tk = _FakeTk
tk_stub.Toplevel = _FakeToplevel
sys.modules.setdefault('tkinter', tk_stub)

# Stub ctypes windll so _apply_click_through is a no-op
if not hasattr(ctypes, 'windll'):
    ctypes.windll = MagicMock()

from src.overlay import OverlayManager
from src.config import DIM_ALL_MIN_OPACITY
from src.monitor import MonitorInfo

M1 = MonitorInfo(r'\\.\DISPLAY1', 0, 0, 1920, 1080)
M2 = MonitorInfo(r'\\.\DISPLAY2', 1920, 0, 2560, 1440)
M3 = MonitorInfo(r'\\.\DISPLAY3', -1280, 0, 1280, 1024)


def _make_manager():
    return OverlayManager(_FakeTk())


def test_rebuild_all_creates_window_for_every_monitor():
    mgr = _make_manager()
    mgr.rebuild_all([M1, M2, M3])
    assert len(mgr._windows) == 3


def test_rebuild_all_sets_dim_all_true():
    mgr = _make_manager()
    mgr.rebuild_all([M1, M2])
    assert mgr.dim_all is True


def test_rebuild_sets_dim_all_false():
    mgr = _make_manager()
    mgr.rebuild_all([M1, M2])
    mgr.rebuild([M1, M2], r'\\.\DISPLAY1')
    assert mgr.dim_all is False


def test_set_mouse_monitor_clamps_mouse_monitor(monkeypatch):
    mgr = _make_manager()
    mgr.rebuild_all([M1, M2])
    mgr._visible = True
    mgr._opacity = 0.05  # below the floor

    opacities = {}
    for w in mgr._windows:
        monkeypatch.setattr(w, 'set_opacity', lambda v, name=w.monitor_name: opacities.__setitem__(name, v))

    mgr.set_mouse_monitor(r'\\.\DISPLAY1')

    assert opacities[r'\\.\DISPLAY1'] == DIM_ALL_MIN_OPACITY
    assert opacities[r'\\.\DISPLAY2'] == 0.05


def test_set_mouse_monitor_above_floor_uses_configured_opacity(monkeypatch):
    mgr = _make_manager()
    mgr.rebuild_all([M1, M2])
    mgr._visible = True
    mgr._opacity = 0.50  # above the floor

    opacities = {}
    for w in mgr._windows:
        monkeypatch.setattr(w, 'set_opacity', lambda v, name=w.monitor_name: opacities.__setitem__(name, v))

    mgr.set_mouse_monitor(r'\\.\DISPLAY1')

    assert opacities[r'\\.\DISPLAY1'] == 0.50
    assert opacities[r'\\.\DISPLAY2'] == 0.50


def test_set_mouse_monitor_no_op_when_hidden(monkeypatch):
    mgr = _make_manager()
    mgr.rebuild_all([M1, M2])
    mgr._visible = False
    mgr._opacity = 0.05
    called = []
    for w in mgr._windows:
        monkeypatch.setattr(w, 'set_opacity', lambda v: called.append(v))
    mgr.set_mouse_monitor(r'\\.\DISPLAY1')
    assert called == []


def test_set_mouse_monitor_none_applies_bare_opacity_to_all(monkeypatch):
    mgr = _make_manager()
    mgr.rebuild_all([M1, M2])
    mgr._visible = True
    mgr._opacity = 0.05

    opacities = {}
    for w in mgr._windows:
        monkeypatch.setattr(w, 'set_opacity', lambda v, name=w.monitor_name: opacities.__setitem__(name, v))

    mgr.set_mouse_monitor(None)

    assert opacities[r'\\.\DISPLAY1'] == 0.05
    assert opacities[r'\\.\DISPLAY2'] == 0.05
