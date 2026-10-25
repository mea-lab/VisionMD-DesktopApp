import numpy as np
from app.analysis.signal_analyzers.gait_steady_step import (
    FEATURE_NAME, UNAVAILABLE, segment_step_times, summarize_step_times,
)
from app.analysis.tasks.gait import GaitTask


def test_complete_steps_only_inside_two_second_boundaries():
    # 10-second segment, alternating half-second steps. End at 8 s is excluded.
    times = np.arange(0, 10, .5)
    events = {'left_down': times[::2] * 30, 'right_down': times[1::2] * 30}
    samples = segment_step_times(events, 300, 30)
    assert len(samples['left']) == 5
    assert len(samples['right']) == 6
    assert np.allclose(samples['left'], .5) and np.allclose(samples['right'], .5)
    assert summarize_step_times([samples])['value_ms'] == 0


def test_within_segment_sd_removes_direction_mean_difference():
    a = np.array([.4, .45, .5, .55, .6])
    segments = [{'left': a, 'right': a}, {'left': a + .4, 'right': a + .4}]
    summary = summarize_step_times(segments)
    assert np.isclose(summary['value_ms'], np.std(a, ddof=1) * 1000)
    assert summary['samples_per_side'] == {'left': 10, 'right': 10}
    assert summary['segments_used'] == 2
    assert len(summary['segment_sds_ms']) == 2
    assert summary['value_ms'] < np.std(np.concatenate([a, a + .4]), ddof=1) * 1000


def test_short_segments_never_fall_back_to_boundary_samples():
    samples = segment_step_times({'left_down': [0, 30, 60], 'right_down': [15, 45, 75]}, 90, 30)
    assert not summarize_step_times([samples])['available']
    assert summarize_step_times([samples])['value_ms'] is None


def test_singleton_segments_do_not_count_toward_variance_minimum():
    segments = [{'left': [.5], 'right': [.5]} for _ in range(8)]
    assert summarize_step_times(segments)['samples_per_side'] == {'left': 0, 'right': 0}
    assert not summarize_step_times(segments)['available']


def test_mirror_average_requires_both_passes():
    task = GaitTask()
    assert task.calculate_average_features({FEATURE_NAME: 10.}, {FEATURE_NAME: 20.})[FEATURE_NAME] == 15.
    assert task.calculate_average_features({FEATURE_NAME: 10.}, {FEATURE_NAME: UNAVAILABLE})[FEATURE_NAME] == UNAVAILABLE
    assert task.calculate_average_features({FEATURE_NAME: UNAVAILABLE}, {FEATURE_NAME: 10.})[FEATURE_NAME] == UNAVAILABLE


def test_missing_side_contact_does_not_make_long_step():
    # Two consecutive left strikes cannot be interpreted as a normal step.
    samples = segment_step_times({'left_down': [60, 90, 105], 'right_down': [75, 120]}, 240, 30)
    assert np.array_equal(samples['left'], [.5])
    assert np.array_equal(samples['right'], [.5, .5])


def test_segment_variances_have_equal_weight_despite_unequal_lengths():
    short = {'left': [.4, .6], 'right': [.4, .6]}
    long = {'left': [.9] * 100, 'right': [.9] * 100}
    result = summarize_step_times([short, long])
    assert np.isclose(result['value_ms'], 100.)
    longer = {'left': [.9] * 500, 'right': [.9] * 500}
    assert np.isclose(summarize_step_times([short, longer])['value_ms'], 100.)
