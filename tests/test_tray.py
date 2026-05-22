from src.tray import _OPACITY_STEPS


def test_opacity_steps_are_five_percent():
    assert len(_OPACITY_STEPS) == 20
    assert abs(_OPACITY_STEPS[0] - 0.05) < 0.001
    assert abs(_OPACITY_STEPS[-1] - 1.0) < 0.001
    for i in range(len(_OPACITY_STEPS) - 1):
        assert abs(_OPACITY_STEPS[i + 1] - _OPACITY_STEPS[i] - 0.05) < 0.001
