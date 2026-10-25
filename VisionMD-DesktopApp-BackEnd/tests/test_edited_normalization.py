import copy
import json
from types import SimpleNamespace

import pytest
from rest_framework.test import APIRequestFactory

from app.analysis.tasks.finger_tap_right import FingerTapRightTask
from app.analysis.tasks.hand_movement_right import HandMovementRightTask
from app.views import update_landmarks as view


def frame():
    full = [[float(i % 5), float(i // 5 + 10), 0.25] for i in range(21)]
    full[5] = [0., 10., .25]
    full[6] = [0., 11., .25]
    full[7] = [0., 12., .25]
    full[8] = [0., 13., .25]
    return full


@pytest.mark.parametrize('name,indices', [
    ('Finger Tap Right', [4, 8]), ('Finger Tap Left', [4, 8]),
    ('Hand Movement Right', [8, 12, 16, 0]), ('Hand Movement Left', [8, 12, 16, 0]),
])
def test_full_landmarks_follow_edits_and_keep_depth(name, indices):
    original = [frame()]
    display = [[original[0][i][:2] for i in indices]]
    display[0][0][0] += .5
    updated, excluded = view.synchronize_hand_landmarks(name, display, original)
    assert updated[0][indices[0]][:2] == display[0][0]
    assert updated[0][indices[0]][2] == .25
    assert original[0][indices[0]][0] != display[0][0][0]
    assert excluded == []


class Analyzer:
    def analyze(self, **kwargs):
        return {'linePlot': {'data': [x / kwargs['normalization_factor'] for x in kwargs['raw_signal']]}}


@pytest.mark.parametrize('task_type,name,strategy', [
    (FingerTapRightTask, 'Finger Tap Right', 'INDEXSIZE'),
    (FingerTapRightTask, 'Finger Tap Right', 'THUMBSIZE'),
    (HandMovementRightTask, 'Hand Movement Right', None),
])
def test_endpoint_recomputes_factor_and_preserves_cache(monkeypatch, task_type, name, strategy):
    class Task(task_type):
        def get_signal_analyzer(self): return Analyzer()
    monkeypatch.setattr(view.importlib, 'import_module', lambda _: SimpleNamespace(**{name.replace(' ', '')+'Task': Task}))
    full = [frame() for _ in range(4)]
    indices = view.HAND_DISPLAY_INDICES[name]
    display = [[f[i][:2] for i in indices] for f in full]
    edited = copy.deepcopy(display[1:3])
    edited[0][0][0] += .5
    if name.startswith('Finger Tap'): edited[0][1][1] += .5
    payload = dict(task_name=name, start_time=1/30, end_time=3/30, fps=30,
                   landmarks=edited, persist_landmark_edits=True,
                   analysis_cache=dict(start_time=0, end_time=4/30, landMarks=display, allLandMarks=full))
    if strategy: payload['norm_strategy'] = strategy
    def request(p):
        return view.update_landmarks(APIRequestFactory().post('/', {'json_data': json.dumps(p)}, format='multipart'))
    response = request(payload)
    assert response.status_code == 200
    expected_full, _ = view.synchronize_hand_landmarks(name, edited, full[1:3])
    task=Task()
    task.task_norm_strategy=strategy or 'PALMSIZE'
    assert response.data['normalization_factor'] == pytest.approx(task.calculate_normalization_factor(expected_full))
    assert response.data['normalization_strategy'] == task.task_norm_strategy
    assert response.data['allLandMarks'] == expected_full
    assert response.data['analysis_cache']['allLandMarks'][0] == full[0]
    assert response.data['analysis_cache']['allLandMarks'][1:3] == expected_full
    assert response.data['analysis_cache']['allLandMarks'][3] == full[3]
    payload.pop('landmarks'); payload.pop('persist_landmark_edits')
    payload['analysis_cache']=response.data['analysis_cache']
    repeated=request(payload)
    assert repeated.data['normalization_factor'] == response.data['normalization_factor']


def test_wrong_hand_joints_are_excluded_from_normalization(monkeypatch):
    class Task(FingerTapRightTask):
        def get_signal_analyzer(self): return Analyzer()
    monkeypatch.setattr(view.importlib, 'import_module', lambda _: SimpleNamespace(FingerTapRightTask=Task))
    full=[frame() for _ in range(3)]
    full[1][8]=[300., 300., .25]
    display=[[f[i][:2] for i in [4,8]] for f in full]
    display[1][1]=[0.,13.]
    payload=dict(task_name='Finger Tap Right',start_time=0,end_time=.1,fps=30,
                 landmarks=display,allLandMarks=full,persist_landmark_edits=True,norm_strategy='INDEXSIZE')
    response=view.update_landmarks(APIRequestFactory().post('/', {'json_data':json.dumps(payload)},format='multipart'))
    assert response.data['normalizationQuality']['excluded_frame_count']==1
    assert response.data['analysis_cache']['normalization_excluded_frames']==[1]
    assert response.data['normalization_factor']==pytest.approx(3.)

    assert any('Normalization excludes' in reason for reason in response.data['analysisQuality']['reasons'])
    payload.pop('landmarks'); payload.pop('persist_landmark_edits')
    payload['analysis_cache']=response.data['analysis_cache']
    again=view.update_landmarks(APIRequestFactory().post('/', {'json_data':json.dumps(payload)},format='multipart'))
    assert again.data['normalization_factor']==pytest.approx(3.)
    assert again.data['normalizationQuality']['excluded_frame_count']==1
