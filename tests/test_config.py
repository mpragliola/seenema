import json
import os
import pytest
from src.config import AppState, load_config, save_config


def test_load_creates_default_when_missing(tmp_path):
    path = tmp_path / "config.json"
    state = load_config(str(path))
    assert state.main_display is None
    assert abs(state.opacity - 0.90) < 0.001
    assert state.autostart is False
    assert state.dim_enabled is False


def test_load_reads_existing_file(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "main_display": r"\\.\DISPLAY2",
        "opacity": 0.70,
        "autostart": True,
        "dim_enabled": False,
    }))
    state = load_config(str(path))
    assert state.main_display == r"\\.\DISPLAY2"
    assert abs(state.opacity - 0.70) < 0.001
    assert state.autostart is True


def test_load_falls_back_on_corrupt_json(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("not json {{{")
    state = load_config(str(path))
    assert state.main_display is None
    assert abs(state.opacity - 0.90) < 0.001


def test_save_and_reload(tmp_path):
    path = str(tmp_path / "config.json")
    state = AppState(main_display=r"\\.\DISPLAY1", opacity=0.80, autostart=False, dim_enabled=False)
    save_config(state, path)
    reloaded = load_config(path)
    assert reloaded.main_display == r"\\.\DISPLAY1"
    assert abs(reloaded.opacity - 0.80) < 0.001


def test_opacity_clamped_on_load(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"opacity": 1.5}))
    state = load_config(str(path))
    assert state.opacity <= 1.0

    path.write_text(json.dumps({"opacity": -0.1}))
    state = load_config(str(path))
    assert state.opacity >= 0.10
