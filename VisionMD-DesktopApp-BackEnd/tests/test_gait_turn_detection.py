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
    assert 4*fps <= start < center < end <= 6*fps

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
