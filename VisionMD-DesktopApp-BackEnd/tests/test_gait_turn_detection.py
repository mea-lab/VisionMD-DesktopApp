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
    assert 2*fps <= start < 4*fps < center < 6*fps < end <= 8*fps

@pytest.mark.parametrize('direction', [1, -1])
def test_straight_walk_with_orientation_artifact_has_no_turn(direction):
    t=np.arange(300)/30
    depth=3000+direction*200*t+20*np.sin(t*10)
    yaw=np.pi*np.clip((t-4)/2,0,1)
    assert confirmed_turn_intervals(depth,yaw,30)==[]

def test_depth_reversal_without_body_turn_has_no_turn():
    t=np.arange(300)/30
    assert confirmed_turn_intervals(3000+500*np.minimum(t,10-t),np.zeros(300),30)==[]

def test_small_depth_jitter_has_no_turn():
    t=np.arange(300)/30
    assert confirmed_turn_intervals(3000+20*np.sin(t),np.pi*np.clip((t-4)/2,0,1),30)==[]

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
    assert start <= 5 * fps and end >= 7 * fps


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
