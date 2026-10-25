import numpy as np
from app.analysis.signal_analyzers.gait_extended_features import ankle_lift_samples, extended_results, velocity
from app.analysis.signal_analyzers.gait_signal_analyzer import GaitSignalAnalyzer


def test_bilateral_variability_excludes_side_offset_and_balances_counts():
    result = extended_results({
        'step_time_left': [.4, .6], 'step_time_right': [.8, 1., 1.2],
        'synthgait_step_length_left': [.4, .4],
        'synthgait_step_length_right': [.8, .8, .8],
    })
    assert np.isclose(result['Average step time'], .75)
    assert np.isclose(result['Step time asymmetry (ms)'], 500)
    assert np.isclose(result['Step time variability (ms; estimated)'], np.sqrt(.03) * 1000)
    assert np.isclose(result['Step length variability'], 0)
    assert np.isclose(result['Average step length'], .6)
    assert np.isclose(result['Step length asymmetry'], .4)


def test_one_side_or_one_observation_does_not_claim_bilateral_precision():
    result = extended_results({'step_time_left': [.5], 'step_time_right': [.6]})
    assert np.isnan(result['Step time variability (ms; estimated)'])
    assert 'Average swing time' not in result
    result = extended_results({'ankle_lift_left': [], 'ankle_lift_right': [10.]})
    assert np.isnan(result['Peak ankle lift (mm; camera vertical)'])


def test_derivative_has_physical_units_and_does_not_bridge_gaps():
    t = np.arange(120) / 60
    assert np.allclose(velocity(3 * t + 7, 60), 3)
    assert np.allclose(velocity(t * t, 60), 2 * t, atol=1e-10)
    assert np.allclose(velocity(np.ones(120), 60), 0, atol=1e-10)
    values = 3 * t
    values[30:40] = np.nan
    result = velocity(values, 60)
    assert np.all(np.isnan(result[30:40]))
    assert np.allclose(result[:30], 3)
    assert np.allclose(result[40:], 3)


def test_ankle_lift_uses_complete_swing_and_removes_linear_stance_drift():
    poses = np.zeros((61, 17, 3))
    poses[:, 6, 1] = .08 + np.arange(61) * .002
    poses[:, 3, 1] = .12 + np.arange(61) * .002
    poses[11:30, 6, 1] += .04 * np.sin(np.linspace(0, np.pi, 19))
    poses[11:30, 3, 1] += .02 * np.sin(np.linspace(0, np.pi, 19))
    events = {f'{side}_{event}': np.asarray(values) for side in ('left', 'right')
              for event, values in (('down', [0, 30, 60]), ('up', [10, 40]))}
    samples = ankle_lift_samples(poses, events, 30)
    assert np.allclose(samples['ankle_lift_left'], [40])
    assert np.allclose(samples['ankle_lift_right'], [20])
    result = extended_results(samples)
    assert np.isclose(result['Peak ankle lift (mm; camera vertical)'], 30)
    assert result['Peak ankle lift valid swings left'] == 1
    poses[20, 6, 1] = np.nan
    assert not ankle_lift_samples(poses, events, 30)['ankle_lift_left'].size


def test_pooling_derivatives_never_differentiates_across_segments():
    def segment(n, offset):
        x = np.full(n, .5)
        samples = {f'{key}_{side}': x for key in ('stance', 'swing', 'step_time', 'step_length')
                   for side in ('left', 'right')}
        samples.update({'double_support': x, 'velocity': [1.], 'velocity_weight': [n],
                        'arm_correlation': [0.], 'arm_correlation_weight': [n],
                        'arm_velocity_left': velocity(np.full(n, offset), 30),
                        'arm_velocity_right': velocity(np.full(n, offset), 30),
                        'torso_ml_velocity': velocity(np.full(n, offset), 30)})
        return samples
    result = GaitSignalAnalyzer.pool_feature_samples([segment(20, 0), segment(30, 10)])
    assert np.isclose(result['Arm swing mean speed (m/s)'], 0)
    assert np.isclose(result['Torso medial-lateral mean speed (m/s)'], 0)


def test_full_analyzer_and_segment_pooling_expose_same_new_measures():
    # Phase-order input, raw mm with camera Y pointing down.
    poses = np.zeros((180, 17, 3))
    poses[:, :, 2] = np.arange(180)[:, None] * 10
    poses[:, [3, 6], 1] = 800
    poses[:, [2, 5], 1] = 400
    poses[:, 3, 0] = -100
    poses[:, 6, 0] = 100
    poses[:, 8, 1] = -600
    poses[:, 7, 1] = -300
    poses[:, 13, 2] += np.arange(180) * 20
    poses[:, 16, 2] -= np.arange(180) * 20
    poses[29:40, 6, 1] -= 40 * np.sin(np.linspace(0, np.pi, 11))
    poses[44:55, 3, 1] -= 20 * np.sin(np.linspace(0, np.pi, 11))
    events = {'left_down': [10, 40, 70, 100, 130], 'left_up': [28, 58, 88, 118, 148],
              'right_down': [25, 55, 85, 115, 145], 'right_up': [43, 73, 103, 133, 163]}
    result, samples = GaitSignalAnalyzer().analyze_gait_video_features(
        events, poses, np.arange(17), 30, return_samples=True)
    pooled = GaitSignalAnalyzer.pool_feature_samples([samples])
    for key in ('Average step length', 'Average velocity', 'Step width',
                'Step length variability', 'Step speed asymmetry',
                'Peak ankle lift (mm; camera vertical)', 'Arm swing mean speed (m/s)',
                'Torso medial-lateral mean speed (m/s)', 'Average step time'):
        assert np.isclose(result[key], pooled[key], equal_nan=True), key
    assert np.isclose(result['Average velocity'], .3)
    assert np.isclose(result['Arm swing mean speed (m/s)'], .6)
    assert result['Peak ankle lift valid swings left'] == 4
    assert np.isclose(result['Peak ankle lift left (mm; camera vertical)'], 10)
    assert np.isclose(result['Peak ankle lift right (mm; camera vertical)'], 5)
    assert result['Temporal variability interpretation'].startswith('Estimated')


def test_unreliable_phase_variability_is_not_reported_or_required():
    poses = np.zeros((100, 17, 3))
    poses[:, :, 2] = np.arange(100)[:, None] * 10
    poses[:, [3, 6], 1] = 800
    poses[:, [2, 5], 1] = 400
    poses[:, 3, 0] = -100
    poses[:, 6, 0] = 100
    poses[:, 8, 1] = -600
    events = {'left_down': [10, 30, 50, 70], 'right_down': [20, 40, 60, 80],
              'left_up': [], 'right_up': []}
    result, samples = GaitSignalAnalyzer().analyze_gait_video_features(
        events, poses, np.arange(17), 30, return_samples=True)
    pooled = GaitSignalAnalyzer.pool_feature_samples([samples])
    for output in (result, pooled, extended_results({
        'swing_left': [.3, .4], 'swing_right': [.4, .5],
        'stance_left': [.6, .7], 'stance_right': [.7, .8]})):
        assert not any('variability' in key.lower() and term in key.lower() for key in output
                       for term in ('swing time', 'stance time', 'double support'))
    assert np.isfinite(result['Average step time'])
    assert np.isfinite(result['Average velocity'])
    assert result['Peak ankle lift valid swings left'] == 0


def test_final_mirror_summary_preserves_new_fields_and_excludes_old_durations():
    from app.analysis.tasks.gait import GaitTask
    original = {'Peak ankle lift left (mm; camera vertical)': 10.,
                'Peak ankle lift right (mm; camera vertical)': 20.,
                'Arm swing mean speed left (m/s)': .1,
                'Arm swing mean speed right (m/s)': .2,
                'Peak ankle lift valid swings left': 3,
                'Peak ankle lift valid swings right': 4,
                'Average velocity': 1., 'Step time asymmetry (ms)': 20.,
                'Temporal variability interpretation': 'Estimated',
                'Average stance time': .6, 'Swing time asymmetry (ms)': 10.,
                'Average double support time': .2}
    mirrored = dict(original)
    mirrored.update({'Peak ankle lift left (mm; camera vertical)': 40.,
                     'Peak ankle lift right (mm; camera vertical)': 30.,
                     'Peak ankle lift valid swings left': 2,
                     'Peak ankle lift valid swings right': 5})
    result = GaitTask().calculate_average_features(original, mirrored)
    assert result['Peak ankle lift left (mm; camera vertical)'] == 20.
    assert result['Peak ankle lift right (mm; camera vertical)'] == 30.
    assert result['Peak ankle lift valid swings left'] == 3
    assert result['Peak ankle lift valid swings right'] == 2
    assert np.isclose(result['Arm swing mean speed left (m/s)'], .15)
    assert result['Average velocity'] == 1.
    assert result['Temporal variability interpretation'] == 'Estimated'
    assert result['Average stance time'] == .6
    assert 'Swing time asymmetry (ms)' not in result
    assert result['Average double support time'] == .2
    assert not any('variability' in key.lower() and term in key.lower() for key in result
                   for term in ('swing time', 'stance time', 'double support'))


def test_phase_means_and_asymmetry_are_retained_without_variability():
    from app.analysis.signal_analyzers.gait_extended_features import phase_time_samples
    events = {'left_down': [0, 30, 60], 'left_up': [18, 48, 78],
              'right_down': [15, 45, 75], 'right_up': [33, 63, 93]}
    result = extended_results(phase_time_samples(events, 30))
    assert np.isclose(result['Average stance time'], .6)
    assert np.isclose(result['Average swing time'], .4)
    assert np.isclose(result['Average double support time'], .2)
    assert np.isclose(result['Stance time asymmetry (ms)'], 0)
    assert np.isclose(result['Swing time asymmetry (ms)'], 0)
    assert not any('variability' in key.lower() and term in key.lower() for key in result
                   for term in ('swing time', 'stance time', 'double support'))


def test_segment_json_preserves_precision_labels_and_missing_numbers():
    from app.analysis.tasks.gait import GaitTask
    result=GaitTask._json_numbers({'Temporal variability interpretation': 'Estimated',
                                 'Unavailable': np.nan, 'Missing': None, 'Speed': np.float64(.8)})
    assert result == {'Temporal variability interpretation': 'Estimated',
                      'Unavailable': None, 'Missing': None, 'Speed': .8}
