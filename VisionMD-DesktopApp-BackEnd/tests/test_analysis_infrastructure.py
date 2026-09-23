import json

import numpy as np

from app.analysis.analysis_quality import assess_analysis_quality
from app.views.import_project_snapshot import _snapshot_data


def test_quality_accepts_line_plot_shape():
    signal = np.sin(np.linspace(0, 8 * np.pi, 240)).tolist()
    assert assess_analysis_quality({"linePlot": {"data": signal}})["status"] == "good"


def test_quality_accepts_multi_signal_shape():
    signal = np.sin(np.linspace(0, 8 * np.pi, 240)).tolist()
    result = {"signals": {"short": [1, 2], "primary": signal}}
    quality = assess_analysis_quality(result)
    assert quality["status"] == "good"
    assert quality["metrics"]["sample_count"] == 240


def test_quality_marks_provisional_ps_for_review():
    signal = np.sin(np.linspace(0, 4 * np.pi, 120)).tolist()
    result = {
        "linePlot": {"data": signal},
        "psPipeline": {
            "engine": "mediapipe_world_landmarks",
            "requires_verification": True,
            "quality": {"pass": True},
        },
    }
    quality = assess_analysis_quality(result)
    assert quality["status"] == "review"
    assert any("verification" in reason for reason in quality["reasons"])


def test_snapshot_envelope_is_load_project_json_compatible():
    data = {"persons": [], "boundingBoxes": [], "tasks": [{"name": "Gait"}]}
    assert _snapshot_data({
        "format": "visionmd-project", "version": 1, "data": data,
    }) == data
