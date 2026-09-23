"""Conservative, task-agnostic quality labels for VisionMD results.

This module does not claim clinical validity. It identifies outputs that are
empty, numerically invalid, flat, or contain unusually isolated jumps. Tasks
with richer diagnostics (currently P/S) may provide stronger evidence.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

QUALITY_VERSION = "visionmd-quality-v1"


def _result_signal(result: dict[str, Any]) -> np.ndarray:
    candidates = []
    line_plot = result.get("linePlot")
    if isinstance(line_plot, dict):
        candidates.append(line_plot.get("data", []))
    signals = result.get("signals")
    if isinstance(signals, dict):
        candidates.extend(signals.values())
    elif isinstance(signals, (list, tuple, np.ndarray)):
        candidates.append(signals)

    numeric = []
    for values in candidates:
        try:
            array = np.asarray(values, dtype=float).reshape(-1)
        except (TypeError, ValueError):
            continue
        if array.size:
            numeric.append(array)
    return max(numeric, key=lambda value: value.size, default=np.empty(0, dtype=float))


def assess_analysis_quality(result: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    metrics: dict[str, Any] = {}
    signal = _result_signal(result)

    if signal.size < 3:
        return {"version": QUALITY_VERSION, "status": "failed",
                "label": "Failed", "reasons": ["No usable angle signal"],
                "metrics": {"sample_count": int(signal.size)}}

    finite = np.isfinite(signal)
    invalid_fraction = float(1.0 - finite.mean())
    metrics.update(sample_count=int(signal.size), invalid_fraction=invalid_fraction)
    if invalid_fraction > 0.10:
        reasons.append("More than 10% of signal samples are invalid")
    valid = signal[finite]
    if valid.size < 3:
        return {"version": QUALITY_VERSION, "status": "failed",
                "label": "Failed", "reasons": reasons or ["Too few valid samples"],
                "metrics": metrics}

    signal_range = float(np.percentile(valid, 95) - np.percentile(valid, 5))
    metrics["robust_range"] = signal_range
    if not math.isfinite(signal_range) or signal_range <= 1e-8:
        return {"version": QUALITY_VERSION, "status": "failed",
                "label": "Failed", "reasons": reasons + ["Signal is flat"],
                "metrics": metrics}

    contiguous = np.interp(np.arange(signal.size), np.flatnonzero(finite), valid)
    steps = np.abs(np.diff(contiguous))
    median_step = float(np.median(steps)) if steps.size else 0.0
    p99_step = float(np.percentile(steps, 99)) if steps.size else 0.0
    jump_ratio = p99_step / max(median_step, 1e-6)
    metrics.update(median_step=median_step, p99_step=p99_step, jump_ratio=jump_ratio)
    if invalid_fraction > 0:
        reasons.append("Signal contains interpolated invalid samples")
    if p99_step > 0.35 * signal_range and jump_ratio > 15:
        reasons.append("Signal contains an unusually isolated jump")

    ps = result.get("psPipeline")
    if isinstance(ps, dict):
        deterministic = ps.get("quality", {})
        temporal = ps.get("temporal_refiner", {})
        metrics["ps_deterministic_pass"] = bool(deterministic.get("pass"))
        metrics["ps_temporal_attempted"] = bool(temporal.get("attempted"))
        metrics["ps_temporal_accepted"] = bool(temporal.get("accepted"))
        metrics["ps_engine"] = ps.get("engine")
        if ps.get("requires_verification"):
            reasons.append("P/S engine requires visual verification")
        if not deterministic.get("pass"):
            if temporal.get("accepted"):
                reasons.append("P/S required learned temporal correction")
            else:
                reasons.append("P/S deterministic quality checks failed")
        if float(deterministic.get("low_confidence_fraction", 0) or 0) > 0.50:
            return {"version": QUALITY_VERSION, "status": "failed",
                    "label": "Failed", "reasons": reasons + ["Most P/S frames are low confidence"],
                    "metrics": metrics}

    status = "review" if reasons else "good"
    return {"version": QUALITY_VERSION, "status": status,
            "label": "Needs review" if status == "review" else "Good",
            "reasons": reasons, "metrics": metrics,
            "disclaimer": "Automated technical quality screen; not a clinical validity assessment."}
