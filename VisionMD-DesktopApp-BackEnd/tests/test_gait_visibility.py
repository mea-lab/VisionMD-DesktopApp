import numpy as np
import pytest
from app.analysis.gait_visibility import full_person_visible, visible_ranges, restrict_walking_ranges


def person():
    points=np.tile([50.,40.,.9],(17,1))
    points[5,:2]=[40,70];points[6,:2]=[60,70]
    points[13,:2]=[40,125];points[14,:2]=[60,125]
    points[15,:2]=[40,170];points[16,:2]=[60,170]
    return points


def test_visible_head_and_both_feet_required():
    points=person();box=[20,30,80,180]
    assert full_person_visible(points,box,100,200)
    for ankle in (15,16):
        missing=points.copy();missing[ankle,2]=.1
        assert not full_person_visible(missing,box,100,200)
    points[:5,2]=.1
    assert not full_person_visible(points,box,100,200)
    assert not full_person_visible(None,box,100,200)


def test_nose_or_ankle_inside_is_insufficient_if_head_or_shoe_crosses_edge():
    points=person();points[:5,1]=4
    assert not full_person_visible(points,[20,3,80,180],100,200)
    points=person();points[15,1]=196
    assert not full_person_visible(points,[20,30,80,197],100,200)
    assert not full_person_visible(person(),[0,30,80,180],100,200)


def test_one_unknown_frame_splits_eligibility_without_filling():
    assert visible_ranges([0,1,1,0,1,1,0])==[[1,3],[4,6]]
    assert visible_ranges([])==[]
    assert restrict_walking_ranges([(0,10),(15,30)],{'frame_ranges':[[2,8],[9,19],[21,28]]},30)==[(2,8),(9,10),(15,19),(21,28)]
    assert restrict_walking_ranges([(0,10)],{'frame_ranges':[]},10)==[]


@pytest.mark.parametrize('ranges',[[[2,1]],[[0,11]],[[2,6],[5,8]],[[0,2.5]],[[True,3]]])
def test_invalid_cached_visibility_rejected(ranges):
    with pytest.raises(ValueError):restrict_walking_ranges([(0,10)],{'frame_ranges':ranges},10)


def test_gait_events_never_bridge_turn_or_invisible_frames(monkeypatch):
    import app.analysis.tasks.gait as module
    from app.analysis.tasks.gait import GaitTask
    monkeypatch.setattr(module,'segment_step_times',lambda *a:{})
    monkeypatch.setattr(module,'summarize_step_times',lambda *a:{'available':False,'value_ms':None})
    monkeypatch.setattr(module,'steady_width_samples',lambda *a:{})
    monkeypatch.setattr(module,'summarize_width',lambda *a:{'available':False})
    monkeypatch.setattr(module,'segment_ankle_length_speed',lambda *a:{'length':{},'speed':{}})
    monkeypatch.setattr(module,'combine_segment_variability',lambda *a,**k:{})
    seen=[]
    class Analyzer:
        def analyze(self,phases,strides,poses,fps,**kwargs):
            seen.append(poses[:,14,2].tolist())
            events={k:np.array([0.,1.]) for k in ['left_down','left_up','right_down','right_up']}
            return {'Average step time':.5},events,{},{}
        def pool_feature_samples(self,samples):return {'Average step time':.5}
    task=GaitTask();task.fps=2;task.start_frame_idx=0
    task.full_person_visibility={'frame_ranges':[[2,10],[15,24]]}
    poses=np.zeros((30,17,3));poses[:,14,2]=np.arange(30)
    signal=np.zeros((30,8))
    analysis=task.analyze_straight_walking_segments(Analyzer(),signal,signal,poses,signal,signal,poses,{'is_turning':True,'start_frame':8,'end_frame':14})
    assert seen==[list(range(2,8))]*2+[list(range(15,24))]*2
    assert [(s['start_frame'],s['end_frame']) for s in analysis['segment_metrics']]==[(2,7),(15,23)]
    assert analysis['quality']['full_person_visibility']==task.full_person_visibility


@pytest.mark.parametrize('turns',[False,True])
def test_turn_search_ignores_partial_person_lead_in_and_preserves_frames(monkeypatch,turns):
    from app.analysis.tasks.gait import GaitTask
    task=GaitTask();task.full_person_visibility={'frame_ranges':[[5,25]]}
    poses=np.arange(30)[:,None,None]*np.ones((30,17,3));seen=[]
    def detect(part, box_heights=None):
        seen.append(part[:,0,0].tolist())
        return {'is_turning':turns,'start_frame':3,'end_frame':6,'boundary_source':'test','candidate_count':1,'transition_guard_seconds':1.0,'tracking_size_checked':False}
    def measure(all_poses,a,b):
        assert np.array_equal(all_poses,poses)
        return {'is_turning':True,'start_frame':a,'end_frame':b}
    monkeypatch.setattr(task,'detect_turn',detect);monkeypatch.setattr(task,'measure_turn_range',measure)
    metadata=task.detect_visible_turn(poses)
    assert seen==[list(range(5,25))]
    if turns:assert (metadata['start_frame'],metadata['end_frame'])==(8,11)


def test_turn_tracking_sizes_follow_video_frame_offsets(monkeypatch):
    from app.analysis.tasks.gait import GaitTask
    task = GaitTask()
    task.start_frame_idx = 100
    task.full_person_visibility = {"frame_ranges": [[5, 25]]}
    task.subject_bounding_boxes = [
        {"frameNumber": 100+i, "data": [{"height": 200+i}]}
        for i in range(30)
    ]
    poses = np.zeros((30, 17, 3))
    def detect(part, box_heights=None):
        assert len(part) == 20
        np.testing.assert_array_equal(box_heights, np.arange(205, 225))
        return {"is_turning": False}
    monkeypatch.setattr(task, "detect_turn", detect)
    assert task.detect_visible_turn(poses) == {"is_turning": False}
