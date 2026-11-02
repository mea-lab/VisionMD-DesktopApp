import numpy as np
import pytest

from app.analysis.signal_analyzers.gait_study_features import stride_samples, study_segment_summaries, pooled_study_features
from app.analysis.signal_analyzers.gait_reporting import public_features, study_table_features, STUDY_FEATURES


def test_stride_samples_use_only_contacts_in_each_segment():
    kp = np.zeros((50, 17, 3))
    kp[:, 0, 2] = np.arange(50) * .1
    kp[:, 3, 2] = kp[:, 6, 2] = np.arange(50) * .1
    events = {'left_down': [0, 20, 40], 'right_down': [10, 30]}
    samples = stride_samples(events, kp, 10)
    assert samples['stride_time_left'].tolist() == [2, 2]
    assert samples['stride_length_left'].tolist() == pytest.approx([2, 2])
    assert pooled_study_features([samples])['Average stride time'] == 2
    # A second segment with only one contact per side cannot form a stride.
    other = stride_samples({'left_down': [0], 'right_down': [10]}, kp, 10)
    assert pooled_study_features([samples, other])['Average stride time'] == 2


def test_asymmetry_formulas_and_segment_weighting():
    a = {'arm_swing_left': [1], 'arm_swing_right': [2],
         'step_time_left': [1, 1], 'step_time_right': [1, 1],
         'step_width_left': [1, 1], 'step_width_right': [2, 2]}
    b = {'arm_swing_left': [1], 'arm_swing_right': [1],
         'step_time_left': [1], 'step_time_right': [1],
         'step_width_left': [1, 1, 1], 'step_width_right': [1, 1, 1]}
    a.update(study_segment_summaries(a)); b.update(study_segment_summaries(b))
    out = pooled_study_features([a, b])
    expected_angle = abs(45 - np.degrees(np.arctan(2))) / 90 * 100
    assert out['Arm-swing amplitude asymmetry (%)'] == pytest.approx(expected_angle * 4 / 6)
    assert out['Step-width asymmetry (%)'] == pytest.approx((200 / 3) * 2 / 5)
    assert public_features(out)['Step-width asymmetry (%)'] == out['Step-width asymmetry (%)']


def test_turns_and_unavailable_rows():
    result = study_table_features({'Average cadence': 100, 'Average stride time': float('nan')}, {'is_turning': False})
    assert len([x for x in STUDY_FEATURES if x in result]) == 25
    assert result['Average stride time'] is None and result['Turn duration (s)'] is None
    result = study_table_features({}, {'is_turning': True, 'duration_seconds': 2, 'mean_angular_speed_degrees_per_second': 90})
    assert result['Turn duration (s)'] == 2 and result['Turn mean angular speed (deg/s)'] == 90
