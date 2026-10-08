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

def _quality_result_with_cycles(peak_values, peak_times=None):
    count = len(peak_values)
    peak_times = peak_times or list(np.arange(count, dtype=float) + 0.5)
    return {
        "linePlot": {"data": np.sin(np.linspace(0, 8 * np.pi, 240)).tolist()},
        "peaks": {"data": peak_values, "time": peak_times},
        "valleys_start": {"data": [0.0] * count,
                          "time": [time - 0.4 for time in peak_times]},
        "valleys_end": {"data": [0.0] * count,
                        "time": [time + 0.4 for time in peak_times]},
    }


def test_quality_accepts_consistent_cycle_morphology():
    report = assess_analysis_quality(
        _quality_result_with_cycles([1.0, 1.05, 0.95, 1.0, 1.02, 0.98])
    )
    assert report["status"] == "good"
    assert report["metrics"]["cycle_count"] == 6


def test_quality_reviews_extreme_cycle_amplitude_dispersion():
    report = assess_analysis_quality(
        _quality_result_with_cycles([1.0, 1.0, 1.0, 3.5, 0.2, 1.0])
    )
    assert report["status"] == "review"
    assert "Cycle amplitudes vary unusually" in report["reasons"]
    check = next(
        item for item in report["checks"]
        if item["name"] == "Cycle amplitude dispersion"
    )
    assert check["outcome"] == "review"
