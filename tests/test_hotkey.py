from src.hotkey import adjust_opacity


def test_adjust_opacity_up():
    assert abs(adjust_opacity(0.50, +1) - 0.55) < 0.001


def test_adjust_opacity_down():
    assert abs(adjust_opacity(0.50, -1) - 0.45) < 0.001


def test_adjust_opacity_clamps_at_max():
    assert abs(adjust_opacity(1.0, +1) - 1.0) < 0.001


def test_adjust_opacity_clamps_at_min():
    assert abs(adjust_opacity(0.05, -1) - 0.05) < 0.001


def test_adjust_opacity_reaches_five_percent():
    # 0.10 - 0.05 = 0.05 (now allowed)
    assert abs(adjust_opacity(0.10, -1) - 0.05) < 0.001


def test_adjust_opacity_snaps_then_steps_up():
    # 0.92 snaps to 0.90 (nearest 5%), then +0.05 = 0.95
    assert abs(adjust_opacity(0.92, +1) - 0.95) < 0.001


def test_adjust_opacity_snaps_then_steps_down():
    # 0.93 snaps to 0.95 (nearest 5%), then -0.05 = 0.90
    assert abs(adjust_opacity(0.93, -1) - 0.90) < 0.001
