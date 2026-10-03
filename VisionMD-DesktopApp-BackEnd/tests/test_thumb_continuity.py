import copy
import numpy as np
import pytest
from app.analysis.tasks.base_task import BaseTask


def hand():
    f=[[0.,0.,0.]for _ in range(21)]
    for n,(mcp,pip,dip,tip)in enumerate([(5,6,7,8),(9,10,11,12),(13,14,15,16),(17,18,19,20)]):
        x=float(n*10)
        for j,y in [(mcp,6.),(pip,4.),(dip,2.),(tip,1.)]:f[j]=[x,y,0.]
    f[1:5]=[[-6.,4.,0.],[-7.,3.,0.],[-8.,2.,0.],[-9.,1.,0.]]
    return f


@pytest.mark.parametrize('length',[1,2,3])
def test_brief_thumb_to_pinky_swap_is_repaired(length):
    frames=[hand()for _ in range(30)]
    for i in range(10,10+length):frames[i][4]=frames[i][19].copy()
    corrected,q=BaseTask.repair_hand_fingertip_identity(frames,fps=30)
    assert q['thumb_identity_violation_frame_count']==length
    assert q['repaired_thumb_frame_count']==length
    assert q['pass']
    for i in range(10,10+length):assert corrected[i][4]==hand()[4]
    for i in list(range(10))+list(range(10+length,30)):assert corrected[i]==frames[i]


def test_long_thumb_swap_is_flagged_and_left_visible():
    frames=[hand()for _ in range(30)]
    for i in range(10,20):frames[i][4]=frames[i][19].copy()
    corrected,q=BaseTask.repair_hand_fingertip_identity(frames,fps=30)
    assert q['thumb_identity_violation_frame_count']==10
    assert q['repaired_thumb_frame_count']==0
    assert not q['pass']
    assert corrected==frames


def test_edge_thumb_failure_is_not_extrapolated():
    frames=[hand()for _ in range(30)]
    frames[0][4]=frames[0][19].copy()
    corrected,q=BaseTask.repair_hand_fingertip_identity(frames,fps=30)
    assert corrected[0][4]==frames[0][4]
    assert not q['pass']
    assert q['repaired_thumb_frame_count']==0


def test_real_thumb_index_contact_is_preserved():
    frames=[hand()for _ in range(30)]
    # A fast valid thumb movement with its IP joint moving consistently.
    for i in [10,11]:
        frames[i][4]=[0.,1.,0.]
        frames[i][3]=[-1.,2.,0.]
    corrected,q=BaseTask.repair_hand_fingertip_identity(frames,fps=30)
    assert corrected==frames
    assert q['thumb_identity_violation_frame_count']==0


def test_smooth_tapping_and_translating_hand_are_unchanged():
    frames=[hand()for _ in range(60)]
    for i,f in enumerate(frames):
        delta=2.*np.sin(i*.4)
        for j in [1,2,3,4]:f[j][0]+=delta
        for point in f:point[0]+=i*.7;point[1]+=i*.3
    corrected,q=BaseTask.repair_hand_fingertip_identity(frames,fps=30)
    assert np.array_equal(corrected,frames)
    assert q['thumb_identity_violation_frame_count']==0


def test_whole_thumb_branch_jump_is_repaired_consistently():
    frames=[hand()for _ in range(30)]
    for j in [1,2,3,4]:frames[10][j][0]+=30.
    corrected,q=BaseTask.repair_hand_fingertip_identity(frames,fps=30)
    assert q['repaired_thumb_frame_count']==1
    for j in [1,2,3,4]:assert corrected[10][j]==hand()[j]


def test_whole_hand_repositioning_is_not_a_thumb_branch_repair():
    frames=[hand()for _ in range(30)]
    for i,f in enumerate(frames):
        for point in f:point[0]+=i*10.
    for j in [1,2,3,4]:frames[10][j][0]+=30.
    corrected,q=BaseTask.repair_hand_fingertip_identity(frames,fps=30)
    assert corrected==frames
    assert q['thumb_identity_violation_frame_count']==0
