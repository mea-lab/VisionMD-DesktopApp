import json
from types import SimpleNamespace

import numpy as np
from rest_framework.test import APIRequestFactory

from app.analysis.analysis_quality import assess_analysis_quality
from app.analysis.tasks.base_task import BaseTask
from app.views import update_landmarks as update_module


def hand_frame():
    frame = [[0.0, 0.0, 0.0] for _ in range(21)]
    for finger, (mcp, pip, dip, tip) in enumerate(
        ((5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20))
    ):
        x = float(finger * 10)
        frame[mcp] = [x, 6.0, 0.0]
        frame[pip] = [x, 4.0, 0.0]
        frame[dip] = [x, 2.0, 0.0]
        frame[tip] = [x, 1.0, 0.0]
    frame[1:5] = [[-6.0, 4.0, 0.0], [-7.0, 3.0, 0.0],
                  [-8.0, 2.0, 0.0], [-9.0, 1.0, 0.0]]
    return frame


def test_short_finger_identity_switch_is_repaired_without_review():
    frames = [hand_frame() for _ in range(20)]
    frames[10][8] = [10.0, 2.0, 0.0]

    corrected, quality = BaseTask.repair_hand_fingertip_identity(frames, fps=30)

    assert quality["pass"] is True
    assert quality["identity_violation_frame_count"] == 1
    assert quality["repaired_identity_frame_count"] == 1
    assert corrected[10][8] == [0.0, 1.0, 0.0]
    report = assess_analysis_quality({
        "linePlot": {"data": list(range(20))},
        "landmarkQuality": quality,
    })
    assert report["label"] == "Good"
    assert any(check["name"] == "Finger landmark identity" for check in report["checks"])


def test_sustained_finger_identity_switch_requires_review():
    frames = [hand_frame() for _ in range(20)]
    for frame in frames[8:13]:
        frame[8] = [10.0, 2.0, 0.0]

    _, quality = BaseTask.repair_hand_fingertip_identity(frames, fps=30)
    assert quality["pass"] is False
    assert quality["long_identity_violation_frame_count"] == 5
    report = assess_analysis_quality({
        "linePlot": {"data": list(range(20))},
        "landmarkQuality": quality,
    })
    assert report["label"] == "Needs review"


def test_manual_edit_replaces_cached_landmark(monkeypatch):
    class Analyzer:
        @staticmethod
        def analyze(**kwargs):
            return {"linePlot": {"data": kwargs["raw_signal"]}}

    class Task:
        task_norm_strategy = None

        @staticmethod
        def calculate_signal(landmarks):
            return [frame[0][0] for frame in landmarks]

        @staticmethod
        def calculate_normalization_factor(_landmarks):
            return 1.0

        @staticmethod
        def get_signal_analyzer():
            return Analyzer()

    monkeypatch.setattr(
        update_module.importlib,
        "import_module",
        lambda _path: SimpleNamespace(FingerTapRightTask=Task),
    )
    original = [[[1.0, 1.0]], [[2.0, 2.0]], [[3.0, 3.0]]]
    edited = [[[1.0, 1.0]], [[20.0, 20.0]], [[3.0, 3.0]]]
    all_landmarks = [hand_frame() for _ in range(3)]
    payload = {
        "task_name": "Finger Tap Right",
        "start_time": 0.0,
        "end_time": 0.1,
        "fps": 30.0,
        "landmarks": edited,
        "allLandMarks": all_landmarks,
        "persist_landmark_edits": True,
        "analysis_cache": {
            "start_time": 0.0,
            "end_time": 0.1,
            "landmark_start_frame": 0,
            "landMarks": original,
            "allLandMarks": all_landmarks,
        },
    }
    request = APIRequestFactory().post(
        "/", {"json_data": json.dumps(payload)}, format="multipart"
    )

    response = update_module.update_landmarks(request)

    assert response.status_code == 200
    assert response.data["landMarks"] == edited
    assert response.data["analysis_cache"]["landMarks"] == edited
