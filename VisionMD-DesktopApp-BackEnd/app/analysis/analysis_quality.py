"""Conservative, task-agnostic quality labels for VisionMD results.

This module does not claim clinical validity. It identifies unusable signals,
tracking discontinuities, and unusual cycle amplitude, duration, or cadence.
Tasks with richer diagnostics (currently finger identity and P/S) may provide
stronger evidence.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

QUALITY_VERSION = "visionmd-quality-v2"


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


def _cycle_morphology(result: dict[str, Any]) -> dict[str, float | int]:
    """Return robust, scale-independent diagnostics for serialized cycles."""
    keys = ("peaks", "valleys_start", "valleys_end")
    if not all(isinstance(result.get(key), dict) for key in keys):
        return {}
    try:
        peak_values = np.asarray(result["peaks"].get("data", []), dtype=float)
        peak_times = np.asarray(result["peaks"].get("time", []), dtype=float)
        opening_values = np.asarray(result["valleys_start"].get("data", []), dtype=float)
        opening_times = np.asarray(result["valleys_start"].get("time", []), dtype=float)
        closing_values = np.asarray(result["valleys_end"].get("data", []), dtype=float)
        closing_times = np.asarray(result["valleys_end"].get("time", []), dtype=float)
    except (TypeError, ValueError):
        return {}
    lengths = {len(values) for values in (
        peak_values, peak_times, opening_values, opening_times,
        closing_values, closing_times,
    )}
    if len(lengths) != 1 or not lengths or len(peak_values) < 4:
        return {}
    stacked = np.column_stack((
        peak_values, peak_times, opening_values, opening_times,
        closing_values, closing_times,
    ))
    if not np.all(np.isfinite(stacked)):
        return {}
    amplitudes = np.minimum(
        peak_values - opening_values, peak_values - closing_values
    )
    durations = closing_times - opening_times
    intervals = np.diff(peak_times)
    if np.any(amplitudes <= 0) or np.any(durations <= 0) or np.any(intervals <= 0):
        return {}

    def robust_cv(values):
        median = float(np.median(values))
        return float(
            1.4826 * np.median(np.abs(values - median))
            / max(abs(median), np.finfo(float).eps)
        )

    median_amplitude = max(
        float(np.median(amplitudes)), np.finfo(float).eps
    )
    return {
        "cycle_count": int(len(amplitudes)),
        "cycle_amplitude_dispersion": float(
            (np.quantile(amplitudes, 0.90) - np.quantile(amplitudes, 0.10))
            / median_amplitude
        ),
        "cycle_duration_robust_cv": robust_cv(durations),
        "peak_interval_robust_cv": robust_cv(intervals),
        "small_cycle_fraction": float(np.mean(amplitudes < 0.50 * median_amplitude)),
    }


def _assess_analysis_quality(result: dict[str, Any]) -> dict[str, Any]:
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
    relative_p99_step = p99_step / max(signal_range, 1e-8)
    metrics["relative_p99_step"] = relative_p99_step
    if p99_step > 0.35 * signal_range and jump_ratio > 15:
        reasons.append("Signal contains an unusually isolated jump")
    elif relative_p99_step > 0.35:
        reasons.append("Signal changes are unusually large relative to its range")

    morphology = _cycle_morphology(result)
    metrics.update(morphology)
    if morphology and morphology["cycle_count"] >= 5:
        if morphology["cycle_amplitude_dispersion"] > 1.00:
            reasons.append("Cycle amplitudes vary unusually")
        if morphology["cycle_duration_robust_cv"] > 0.40:
            reasons.append("Cycle durations vary unusually")
        if morphology["peak_interval_robust_cv"] > 0.30:
            reasons.append("Peak cadence is unusually irregular")

    landmark_quality = result.get("landmarkQuality")
    if isinstance(landmark_quality, dict):
        violation_count = int(landmark_quality.get("identity_violation_frame_count", 0) or 0)
        repaired_count = int(landmark_quality.get("repaired_identity_frame_count", 0) or 0)
        long_count = int(landmark_quality.get("long_identity_violation_frame_count", 0) or 0)
        # Older cached results marked any >1% repaired frames as failed. A
        # fully repaired short run is usable; only unresolved/sustained runs
        # require review. Preserve other explicit failures such as too few frames.
        repaired_short_runs = (
            violation_count > 0
            and repaired_count >= violation_count
            and long_count == 0
        )
        identity_pass = bool(landmark_quality.get("pass")) or repaired_short_runs
        metrics["landmark_identity_pass"] = identity_pass
        metrics["landmark_identity_violation_fraction"] = float(
            landmark_quality.get("identity_violation_fraction", 0) or 0
        )
        metrics["landmark_identity_repaired_frames"] = repaired_count
        metrics["landmark_identity_long_violation_frames"] = long_count
        if not identity_pass:
            reasons.extend(landmark_quality.get("reasons") or
                           ["Hand landmark identities failed continuity checks"])

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

def assess_analysis_quality(result: dict[str, Any]) -> dict[str, Any]:
    """Attach auditable evidence without changing the existing classification.

    Only evaluated checks are emitted: a fatal early exit deliberately leaves
    later checks absent. Values are from the same signal used by the assessor.
    """
    report = _assess_analysis_quality(result)
    metrics = report["metrics"]
    checks = []
    def check(name, observed, rule, triggered, severity):
        checks.append({"name": name, "observed": observed, "rule": rule,
                       "outcome": severity if triggered else "pass"})
    check("Sample count", metrics["sample_count"], "Fail when fewer than 3 samples",
          metrics["sample_count"] < 3, "failed")
    if "invalid_fraction" in metrics:
        fraction = metrics["invalid_fraction"]
        check("Invalid samples", fraction,
              "Review when fraction > 0; additional warning above 0.10",
              fraction > 0, "review")
        valid_count = int(np.isfinite(_result_signal(result)).sum())
        check("Valid sample count", valid_count, "Fail when fewer than 3 finite samples",
              valid_count < 3, "failed")
    if "robust_range" in metrics:
        value = metrics["robust_range"]
        check("Robust signal range (95th minus 5th percentile)", value,
              "Fail when range <= 0.00000001 or not finite",
              not math.isfinite(value) or value <= 1e-8, "failed")
    if "jump_ratio" in metrics:
        check("Isolated jumps",
              {"p99_step": metrics["p99_step"], "median_step": metrics["median_step"],
               "jump_ratio": metrics["jump_ratio"],
               "range_threshold": 0.35 * metrics["robust_range"]},
              "Review only if p99 absolute step > 0.35 × robust range AND "
              "p99 / max(median absolute step, 0.000001) > 15",
              metrics["p99_step"] > .35 * metrics["robust_range"] and
              metrics["jump_ratio"] > 15, "review")
    if "relative_p99_step" in metrics:
        check(
            "Relative signal change",
            metrics["relative_p99_step"],
            "Review when the 99th-percentile absolute step exceeds 0.35 × "
            "the robust signal range",
            metrics["relative_p99_step"] > 0.35,
            "review",
        )
    if "cycle_count" in metrics:
        enough_cycles = metrics["cycle_count"] >= 5
        check(
            "Cycle amplitude dispersion",
            metrics["cycle_amplitude_dispersion"],
            "Review with at least 5 cycles when the 10th-to-90th percentile "
            "amplitude range divided by median amplitude exceeds 1.00",
            enough_cycles and metrics["cycle_amplitude_dispersion"] > 1.00,
            "review",
        )
        check(
            "Cycle duration variability",
            metrics["cycle_duration_robust_cv"],
            "Review with at least 5 cycles when robust duration CV exceeds 0.40",
            enough_cycles and metrics["cycle_duration_robust_cv"] > 0.40,
            "review",
        )
        check(
            "Peak cadence variability",
            metrics["peak_interval_robust_cv"],
            "Review with at least 5 cycles when robust peak-interval CV exceeds 0.30",
            enough_cycles and metrics["peak_interval_robust_cv"] > 0.30,
            "review",
        )
    if "landmark_identity_pass" in metrics:
        diagnostic = result["landmarkQuality"]
        check(
            "Finger landmark identity",
            {
                "pass": diagnostic.get("pass"),
                "identity_violation_frame_count": diagnostic.get("identity_violation_frame_count"),
                "identity_violation_fraction": diagnostic.get("identity_violation_fraction"),
                "repaired_identity_frame_count": diagnostic.get("repaired_identity_frame_count"),
                "long_identity_violation_frame_count": diagnostic.get("long_identity_violation_frame_count"),
                "fallback_recommended": diagnostic.get("fallback_recommended"),
                "recommended_engine": diagnostic.get("recommended_engine"),
            },
            "Review when fingertip identity failures persist too long for safe repair "
            "or the identity check otherwise fails",
            not metrics["landmark_identity_pass"],
            "review",
        )
    if "ps_deterministic_pass" in metrics:
        ps = result["psPipeline"]
        diagnostic = ps.get("quality", {})
        check("P/S visual verification", bool(ps.get("requires_verification")),
              "Review when the engine requires verification",
              bool(ps.get("requires_verification")), "review")
        check("P/S deterministic checks",
              {"pass": metrics["ps_deterministic_pass"], "diagnostics": diagnostic,
               "temporal_attempted": metrics["ps_temporal_attempted"],
               "temporal_accepted": metrics["ps_temporal_accepted"]},
              "Review when deterministic checks fail, even if temporal correction is accepted",
              not metrics["ps_deterministic_pass"], "review")
        fraction = float(diagnostic.get("low_confidence_fraction", 0) or 0)
        check("P/S low-confidence fraction", fraction,
              "Fail when fraction > 0.50 (missing value defaults to 0)",
              fraction > .50, "failed")
    report.update(
        evidence_version=2, checks=checks,
        signal_selection="Longest numeric signal in linePlot.data or signals; ties use first.",
        decision_rule="Failed checks take priority; otherwise any review reason means "
                      "Needs review; otherwise Good. Later checks are not run after a fatal failure.",
        disclaimer="Automated technical quality screen; not a clinical validity assessment. "
                   "Good does not guarantee correct tracking, angles, or clinical features.")
    return report
