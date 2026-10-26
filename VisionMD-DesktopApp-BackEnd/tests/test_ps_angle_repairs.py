import numpy as np
import pytest
from app.analysis.tasks._wilor_ps_pipeline import repair_short_flip_intervals
from app.analysis.tasks._ps_cross_crop_repair import repair_cross_crop_branch


def test_single_outlier_does_not_shift_the_intervening_real_movement():
    # The farther exit has slightly better boundary cost; it must not consume
    # the opposite jump immediately after the first outlier.
    original = np.array([40,189,41,41,38,30,11,-17,-49,-71,-113,-114,17,-135.])
    repaired, flags = repair_short_flip_intervals(original, max_interval_frames=18)
    np.testing.assert_array_equal(repaired[2:12], original[2:12])
    assert flags[1] and flags[12]
    assert not flags[2:12].any()


def test_constant_offset_interval_preserves_observed_motion():
    values = np.array([0,5,185,200,215,35,40.])
    repaired, _ = repair_short_flip_intervals(values)
    np.testing.assert_array_equal(repaired, [0,5,5,20,35,35,40])


def wave():
    fps = 30.
    t = np.arange(270)/fps
    return 95*np.cos(2*np.pi*t), fps


def test_cross_crop_winding_repair_preserves_good_cycles():
    reference, fps = wave()
    original = reference.copy()
    original[140:] += 360
    repaired, info = repair_cross_crop_branch(original, reference, fps)
    assert info['accepted'] and info['requires_visual_verification']
    np.testing.assert_allclose(repaired, reference, atol=1e-10)


@pytest.mark.parametrize('case', ['normal', 'unmatched', 'multiple', 'nonfinite', 'fps'])
def test_cross_crop_rejects_unsupported_corrections(case):
    reference, fps = wave()
    original = reference.copy()
    if case != 'normal': original[140:] += 360
    if case == 'unmatched': reference = 150*np.sin(np.arange(270))
    if case == 'multiple': original[220:] -= 360
    if case == 'nonfinite': reference[100] = np.nan
    if case == 'fps': fps = 0
    repaired, info = repair_cross_crop_branch(original, reference, fps)
    assert not info['accepted']
    np.testing.assert_array_equal(repaired, original)
