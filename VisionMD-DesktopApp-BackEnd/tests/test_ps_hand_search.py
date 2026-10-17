import numpy as np
import pytest
from app.analysis.tasks._ps_hand_search import (expanded_search_box,
    associated_boxes, track_search_quality)

SUBJECT = {'x': 89, 'y': 393, 'width': 717, 'height': 1444}


def test_original_regression_box_includes_extended_hand():
    box = expanded_search_box(SUBJECT,1080,1920,.25)
    assert box.tolist() == [0,32,986,1920]
    assert box[0] < 89 and box[1] < 393


def test_invalid_subject_does_not_become_valid_through_padding():
    with pytest.raises(ValueError):
        expanded_search_box({'x':1100,'y':10,'width':20,'height':20},1080,1920,.5)


def test_reach_envelope_keeps_extended_hand_excludes_remote_person():
    boxes = [[20,400,100,500], [1500,400,1600,500]]
    assert associated_boxes(boxes,SUBJECT).tolist() == [boxes[0]]


def test_sparse_detections_do_not_pass_by_interpolation():
    track=[(i,np.array([100,100,150,150])) for i in range(0,120,10)]
    q=track_search_quality(track,120,5,60,[0,0,1080,1920],1080,1920)
    assert q['coverage'] == .5 and not q['pass']


def test_long_gap_fails_even_with_high_total_coverage():
    track=[(i,np.array([100,100,150,150])) for i in range(0,600,5)
           if not 200 <= i < 240]
    q=track_search_quality(track,600,5,60,[0,0,1080,1920],1080,1920)
    assert q['coverage'] > .8 and not q['pass']
    assert q['max_gap_seconds'] > .5


def test_artificial_edge_triggers_retry_but_image_edge_does_not():
    track=[(i,np.array([1,100,51,150])) for i in range(0,120,5)]
    assert track_search_quality(track,120,5,60,[0,0,1080,1920],1080,1920)['pass']
    assert not track_search_quality(track,120,5,60,[1,0,1080,1920],1080,1920)['pass']


@pytest.mark.parametrize('recover', [True, False])
def test_localizer_retries_and_refuses_unresolved_tracks(monkeypatch, recover):
    from types import SimpleNamespace
    from app.analysis.tasks import _pronation_supination as ps
    from app.analysis.tasks.hand_pronation_right import HandPronationRightTask

    class Capture:
        def __init__(self, path): pass
        def set(self, *args): pass
        def read(self): return True, np.zeros((200,200,3),np.uint8)
        def release(self): pass

    class Model:
        calls = 0
        def predict(self, crop, **kwargs):
            self.calls += 1
            present = (self.calls % 2 == 0) or (recover and self.calls > 12)
            coords = np.array([[40.,50.,70.,80.]])
            tensor = SimpleNamespace(cpu=lambda: SimpleNamespace(numpy=lambda: coords))
            boxes = SimpleNamespace(xyxy=tensor) if present else None
            class Boxes:
                xyxy = tensor
                def __len__(self): return 1
            return [SimpleNamespace(boxes=Boxes() if present else None)]

    monkeypatch.setattr(ps.cv2,'VideoCapture',Capture)
    monkeypatch.setattr(ps.BaseTask,'correct_frame_orientation',lambda frame,rotation: frame)
    monkeypatch.setattr(ps,'_HAND_DEVICE','cpu')
    monkeypatch.setattr(ps,'run_with_device_fallback',lambda f,*a,**k:(f('cpu'),'cpu'))
    task=HandPronationRightTask()
    task.original_bounding_box={'x':50,'y':10,'width':100,'height':180}
    task.video_file_path='unused';task.video_fps=60;task.video_rotation=0
    task.task_start_frame_idx=0;task.task_end_frame_idx=60
    if recover:
        result=task._localize(Model())
        assert result[-1] == 1.
    else:
        with pytest.raises(ValueError,match='remains unreliable'):
            task._localize(Model())
    assert task._localization['expanded_retry']
    assert len(task._localization['attempts']) == 2


def test_ps_cache_key_changes_with_search_version(monkeypatch,tmp_path):
    from app.analysis import analysis_cache
    from app.analysis.tasks import _ps_hand_search
    monkeypatch.setattr(analysis_cache,'_project',lambda video_id:tmp_path)
    old=analysis_cache.cache_key('1','hand_pronation_right','{}')
    other=analysis_cache.cache_key('1','finger_tap_right','{}')
    monkeypatch.setattr(_ps_hand_search,'PS_SEARCH_VERSION','next-version')
    assert old != analysis_cache.cache_key('1','hand_pronation_right','{}')
    assert other == analysis_cache.cache_key('1','finger_tap_right','{}')
