"""Regression checks requiring no model weights or GPU inference."""
import csv
import json
import sys

import numpy as np
import pytest

from app.analysis.analysis_quality import assess_analysis_quality, _assess_analysis_quality
from batch_processing.export_results import export_companions


@pytest.mark.parametrize("signal", [[], [1], [0]*10, [float("nan")]*10,
    np.sin(np.linspace(0, 20, 200)).tolist(), [0, 1, float("nan"), 2, 3]])
def test_evidence_preserves_decision(signal):
    result = {"linePlot": {"data": signal}}
    old = _assess_analysis_quality(result)
    new = assess_analysis_quality(result)
    assert new["status"] == old["status"]
    assert new["reasons"] == old["reasons"]
    assert new["checks"]
    json.dumps(new, allow_nan=False)


def test_ps_evidence_contains_actual_fraction_and_diagnostics():
    result = {"linePlot": {"data": np.sin(np.linspace(0, 20, 200)).tolist()},
              "psPipeline": {"quality": {"pass": False, "low_confidence_fraction": .7},
                             "temporal_refiner": {"attempted": True, "accepted": False}}}
    report = assess_analysis_quality(result)
    assert report["status"] == "failed"
    check = next(c for c in report["checks"] if c["name"] == "P/S low-confidence fraction")
    assert check["observed"] == .7
    assert check["outcome"] == "failed"


@pytest.mark.parametrize("schema", ["line", "gait", "tremor", "empty"])
def test_companions(tmp_path, schema):
    signal = np.sin(np.linspace(0, 20, 200)).tolist()
    if schema == "line":
        result = {"linePlot": {"data": signal, "time": (5+np.arange(200)/30).tolist()},
                  "radarTable": {"Frequency": 2.1, "MeanAmplitude": 120}}
    elif schema in ("gait", "tremor"):
        result = {"signals": {"A": signal, "B": signal},
                  "Estimated frequency (Hz)": 2.1}
    else:
        result = {}
    result["analysisQuality"] = assess_analysis_quality(result)
    paths = export_companions(result, tmp_path/"result.json", fps=30,
                              task=schema, video="test.mp4", candidate="candidate_001")
    assert open(paths["signal_png"], "rb").read(8) == b"\x89PNG\r\n\x1a\n"
    with open(paths["features_csv"], newline="") as stream:
        rows = dict(list(csv.reader(stream))[1:])
    assert rows["estimated_quality"] == result["analysisQuality"]["label"]
    if schema == "line":
        assert rows["radarTable.Frequency"] == "2.1"
    elif schema != "empty":
        assert rows["Estimated frequency (Hz)"] == "2.1"

def test_plot_uses_saved_cycle_events(tmp_path, monkeypatch):
    from matplotlib.axes import Axes
    calls = []
    original = Axes.scatter
    def capture(self, x, y, *args, **kwargs):
        calls.append((list(x), list(y), kwargs.get("label"), kwargs.get("color")))
        return original(self, x, y, *args, **kwargs)
    monkeypatch.setattr(Axes, "scatter", capture)
    result = {
        "linePlot": {"time": [5, 6, 7, 8, 9], "data": [0, 2, -1, 3, 0]},
        "peaks": {"time": [6, 8], "data": [2, 3]},
        "valleys_start": {"time": [5], "data": [0]},
        "valleys_end": {"time": [7, 9], "data": [-1, 0]},
    }
    result["analysisQuality"] = assess_analysis_quality(result)
    export_companions(result, tmp_path/"events.json", fps=30,
                      task="Finger Tap Left", video="test.mp4", candidate="001")
    assert calls == [
        ([6, 8], [2, 3], "Peak values", "#decd6d"),
        ([5], [0], "Valley start", "#76B041"),
        ([7, 9], [-1, 0], "Valley end", "red"),
    ]


def test_batch_exports_only_the_selected_result(tmp_path, monkeypatch):
    from batch_processing import batch_analyze

    source = tmp_path / "sample.mp4"
    source.write_bytes(b"video")
    output_dir = tmp_path / "results"
    output_dir.mkdir()
    (output_dir / "sample_candidate_001_finger_tap_right.json").write_text("legacy")
    candidates = [
        {"candidate_id": "candidate_001", "bbox_xyxy": [0, 0, 10, 10]},
        {"candidate_id": "candidate_002", "bbox_xyxy": [10, 0, 20, 10]},
    ]
    info = {"fps": 30.0, "duration": 1.0, "frame_count": 30,
            "width": 20, "height": 10, "rotation": 0,
            "candidates": candidates}

    monkeypatch.setattr(batch_analyze, "YOLO", lambda _weights: object())
    monkeypatch.setattr(batch_analyze, "prepare_analysis_video", lambda video, _root: video)
    monkeypatch.setattr(batch_analyze, "discover", lambda *_args: info)
    monkeypatch.setattr(batch_analyze, "analyze", lambda _video, _info, candidate, *_args: {
        "linePlot": {"data": [0, candidate["bbox_xyxy"][0] / 20 + .1, 0],
                     "time": [0, .5, 1]},
        "peaks": {"data": [], "time": []},
    })
    monkeypatch.setattr(batch_analyze, "project_snapshot",
        lambda _video, _info, candidate, *_args: {"selected": candidate["candidate_id"]})

    def fake_companions(_result, result_path, **_kwargs):
        png = result_path.with_name(result_path.stem + "_signal.png")
        csv_path = result_path.with_name(result_path.stem + "_features.csv")
        png.write_bytes(b"png")
        csv_path.write_text("feature,value\n")
        return {"signal_png": str(png), "features_csv": str(csv_path)}

    monkeypatch.setattr(batch_analyze, "export_companions", fake_companions)
    monkeypatch.setattr(sys, "argv", ["batch_analyze.py", str(source), "--task",
        "finger_tap_right", "--weights", str(tmp_path / "weights.pt"),
        "--output-dir", str(output_dir), "--device", "cpu"])

    batch_analyze.main()

    names = {path.name for path in output_dir.iterdir()}
    assert len(names) == 5
    assert not any("candidate_" in name for name in names)
    project = json.loads((output_dir / "sample_finger_tap_right_visionmd_project.json").read_text())
    assert project["selected"] == "candidate_002"
    manifest = json.loads((output_dir / "sample_finger_tap_right_manifest.json").read_text())
    assert manifest["status"] == "completed"
    assert "candidates" not in manifest
