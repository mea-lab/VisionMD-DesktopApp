import numpy as np
from app.analysis.detectors.subject_candidates import rank_subject_candidates

def test_visible_foreground_pose_is_suggested_over_background():
    sample=lambda area,pose: {'area':area,'pose_quality':pose,'confidence':.9}
    candidates=rank_subject_candidates({1:[sample(1000,.3)]*5,2:[sample(40000,.9)]*10},10,100000)
    assert [c['id'] for c in candidates]==[2,1]
    assert len(candidates)==2

def test_empty_video_has_no_suggestion():
    assert rank_subject_candidates({},0,0)==[]

def test_ties_are_deterministic_and_brief_people_are_retained():
    sample={'area':1000,'pose_quality':.8,'confidence':.9}
    assert [c['id'] for c in rank_subject_candidates({2:[sample],1:[sample]},10,100000)]==[1,2]
