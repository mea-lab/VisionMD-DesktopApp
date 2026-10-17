import numpy as np
import pytest
from app.analysis.signal_analyzers.gait_turn_detection import confirmed_turn_intervals

@pytest.mark.parametrize('direction', [1, -1])
@pytest.mark.parametrize('fps', [15, 30, 60])
def test_near_and_far_turns(direction, fps):
    t=np.arange(10*fps)/fps
    depth=3000+direction*500*np.minimum(t,10-t)
    yaw=np.pi*np.clip((t-4)/2,0,1)
    turns=confirmed_turn_intervals(depth,yaw,fps)
    assert len(turns)==1
    start,end,center,_=turns[0]
    assert 4*fps <= start < 4.5*fps < center < 5.5*fps < end <= 6*fps

@pytest.mark.parametrize('direction', [1, -1])
def test_straight_walk_with_orientation_artifact_has_no_turn(direction):
    t=np.arange(300)/30
    depth=3000+direction*200*t+20*np.sin(t*10)
    yaw=np.pi*np.clip((t-4)/2,0,1)
    assert confirmed_turn_intervals(depth,yaw,30)==[]

def test_depth_reversal_without_body_turn_has_no_turn():
    t=np.arange(300)/30
    assert confirmed_turn_intervals(3000+500*np.minimum(t,10-t),np.zeros(300),30)==[]

def test_turn_in_place_does_not_require_translation():
    t=np.arange(300)/30
    turns = confirmed_turn_intervals(3000+20*np.sin(t),np.pi*np.clip((t-4)/2,0,1),30)
    assert len(turns) == 1


def test_stationary_orientation_jitter_is_not_a_turn():
    t=np.arange(300)/30
    assert confirmed_turn_intervals(3000+20*np.sin(t),.1*np.sin(t),30) == []

def test_missing_depth_has_no_turn():
    assert confirmed_turn_intervals(np.full(300,np.nan),np.zeros(300),30)==[]

@pytest.mark.parametrize("fps", [15, 30, 60])
def test_turn_with_rotation_depth_double_peak(fps):
    t = np.arange(12 * fps) / fps
    depth = 3000 + 500 * np.minimum(t, 12 - t)
    depth += 1300 * np.exp(-((t - 5.3) / .25) ** 2)
    depth += 1300 * np.exp(-((t - 6.7) / .25) ** 2)
    yaw = np.pi * np.clip((t - 5) / 2, 0, 1)
    turns = confirmed_turn_intervals(depth, yaw, fps)
    assert len(turns) == 1
    start, end, _, _ = turns[0]
    assert 5 * fps <= start <= 5.5 * fps and 6.5 * fps <= end <= 7 * fps


def test_tracking_size_vetoes_spurious_3d_reversal():
    t = np.arange(360) / 30
    depth = 3000 + 500 * np.minimum(t, 12 - t)
    yaw = np.pi * np.clip((t - 5) / 2, 0, 1)
    assert confirmed_turn_intervals(depth, yaw, 30)
    assert confirmed_turn_intervals(depth, yaw, 30, box_heights=100 + 20*t) == []


def test_fixed_roi_is_not_direction_evidence():
    t = np.arange(360) / 30
    depth = 3000 + 500 * np.minimum(t, 12 - t)
    yaw = np.pi * np.clip((t - 5) / 2, 0, 1)
    assert confirmed_turn_intervals(depth, yaw, 30, box_heights=np.full(len(t), 300))


def test_invalid_tracking_size_is_not_used():
    t = np.arange(360) / 30
    depth = 3000 + 500 * np.minimum(t, 12 - t)
    yaw = np.pi * np.clip((t - 5) / 2, 0, 1)
    assert confirmed_turn_intervals(depth, yaw, 30, box_heights=np.full(len(t), np.nan)) == []


@pytest.mark.parametrize('fps', [15, 30, 60])
def test_initial_standing_turn_and_later_turnaround_are_both_retained(fps):
    t = np.arange(20 * fps) / fps
    yaw = np.pi * np.clip((t-2)/2, 0, 1) + np.pi * np.clip((t-11)/2, 0, 1)
    depth = 2400 + 900 * np.clip(t-4, 0, 8) - 900 * np.maximum(t-13, 0)
    turns = confirmed_turn_intervals(depth, yaw, fps)
    assert len(turns) == 2
    assert 2 <= turns[0][0]/fps <= 2.5
    assert 3.5 <= turns[0][1]/fps <= 4
    assert 11 <= turns[1][0]/fps <= 11.5
    assert 12.5 <= turns[1][1]/fps <= 13


def test_standing_quarter_turn_uses_the_same_minimum_angle():
    t = np.arange(300) / 30
    yaw = .5 * np.pi * np.clip((t-4)/2, 0, 1)
    assert len(confirmed_turn_intervals(np.full(len(t), 3000.), yaw, 30)) == 1
