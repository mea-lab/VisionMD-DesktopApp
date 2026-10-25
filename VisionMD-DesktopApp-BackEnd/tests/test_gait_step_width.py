import numpy as np
from app.analysis.signal_analyzers.gait_step_width import (
    foot_line_widths, steady_width_samples, summarize_width, POOLED_FEATURE, WITHIN_FEATURE,
)
from app.analysis.tasks.gait import GaitTask
from app.analysis.signal_analyzers.gait_steady_step import UNAVAILABLE
from app.analysis.signal_analyzers.gait_signal_analyzer import GaitSignalAnalyzer


def test_opposite_foot_line_distance_and_rigid_transform_invariance():
    left = np.array([[.12, .5], [.12, 1.5], [.12, 2.5]])
    right = np.array([[0., 0.], [0., 1.], [0., 2.], [0., 3.]])
    frames_l, frames_r = [15, 45, 75], [0, 30, 60, 90]
    base = foot_line_widths(frames_l, left, frames_r, right)
    assert np.allclose(base['widths'], .12)
    assert np.array_equal(base['sides'], [6, 3, 6, 3, 6])
    angle = .7;rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    rotated = foot_line_widths(frames_l, left @ rotation + [2, 4], frames_r, right @ rotation + [2, 4])
    assert np.allclose(rotated['widths'], base['widths'])


def test_degenerate_lines_and_repeated_side_contacts_have_no_axis_fallback():
    assert not foot_line_widths([15], [[.12, .5]], [0, 30], [[0, 0], [0, 0]])['widths'].size
    assert not foot_line_widths([15, 20], [[.12, .5], [.12, .6]], [0, 30], [[0, 0], [0, 1]])['widths'].size


def test_two_seconds_excluded_from_all_three_contact_endpoints():
    frames = np.arange(0, 300, 15);poses = np.zeros((300, 17, 3))
    poses[:, 10, 2] = np.arange(300) * 10
    poses[:, 13, 2] = np.arange(300) * 10
    poses[:, 13, 0] = 120
    events = {'left_down': frames[1::2], 'right_down': frames[::2]}
    samples = steady_width_samples(events, poses, 30)
    assert len(samples['left']) == 5 and len(samples['right']) == 5
    assert np.allclose(np.r_[samples['left'], samples['right']], .12)
    assert summarize_width([samples])['available']
    assert np.isclose(summarize_width([samples])['pooled_sd_m'], 0)


def test_pooled_and_within_segment_width_sd_are_distinct():
    a=np.array([.1, .11, .12, .13, .14]);segments=[{'left':a,'right':a},{'left':a+.04,'right':a+.04}]
    stats=summarize_width(segments)
    assert np.isclose(stats['within_segment_sd_m'], np.std(a,ddof=1))
    assert np.isclose(stats['pooled_sd_m'], np.std(np.r_[a,a+.04],ddof=1))
    assert stats['pooled_sd_m']>stats['within_segment_sd_m']


def test_width_availability_and_mirror_handling():
    assert not summarize_width([{'left':[.1]*4,'right':[.1]*5}])['available']
    task=GaitTask()
    assert POOLED_FEATURE not in task.calculate_average_features({POOLED_FEATURE:.02},{POOLED_FEATURE:.04})
    for feature in [WITHIN_FEATURE]:
        assert np.isclose(task.calculate_average_features({feature:.02},{feature:.04})[feature],.03)
        assert task.calculate_average_features({feature:.02},{feature:UNAVAILABLE})[feature]==UNAVAILABLE


def test_missing_triplets_do_not_make_other_features_unavailable():
    poses=np.zeros((60,17,3));poses[:,:,2]=np.arange(60)[:,None]*10;poses[:,3,0]=-100;poses[:,6,0]=100
    result,samples=GaitSignalAnalyzer().analyze_gait_video_features(
        {'left_down':[10],'right_down':[0,20],'left_up':[],'right_up':[]},poses,np.arange(17),30,return_samples=True)
    # One complete triplet gives left width only; preserve other valid metrics.
    assert samples['step_width_left'].size==1 and samples['step_width_right'].size==0
    assert np.isfinite(result['Average step time'])
    assert np.isnan(result['Step width variability'])
