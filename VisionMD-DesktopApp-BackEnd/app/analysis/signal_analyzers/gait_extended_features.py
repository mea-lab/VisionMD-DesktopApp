"""Bilateral gait summaries and camera-vertical ankle-lift proxies.

All positions are metres; velocities are m/s. Keep signed velocity samples
until summarizing speed, and differentiate each straight segment separately.
"""
import numpy as np
from scipy.signal import savgol_filter


def finite(values):
    values = np.asarray(values, dtype=float)
    return values[np.isfinite(values)]


def velocity(values, fps):
    """Local quadratic derivative over about 0.2 s, without padding gaps.

    Long enough tracks use a Savitzky–Golay fit; short tracks use finite
    differences. Nonfinite runs remain unavailable rather than being bridged.
    """
    values = np.asarray(values, dtype=float)
    if not np.isfinite(fps) or fps <= 0:
        raise ValueError("FPS must be positive and finite.")
    result = np.full(values.shape, np.nan)
    valid = np.isfinite(values)
    edges = np.flatnonzero(np.diff(np.r_[False, valid, False]))
    for start, end in zip(edges[::2], edges[1::2]):
        track = values[start:end]
        if len(track) < 2:
            continue
        window = max(5, int(round(0.2 * fps)) | 1)
        window = min(window, len(track) if len(track) % 2 else len(track) - 1)
        if window >= 5:
            result[start:end] = savgol_filter(
                track, window, 2, deriv=1, delta=1.0 / fps, mode="interp"
            )
        else:
            result[start:end] = np.gradient(track, 1.0 / fps)
    return result


def ankle_lift_samples(kp, events, fps):
    """One peak per complete swing above a drifting stance-height baseline.

    kp is phase-ordered, Y-up, in metres. This is camera-vertical ankle lift,
    not toe/sole clearance. Stance medians on either side of a swing remove
    linear vertical drift (including straight travel in a tilted camera view).
    Require complete bracketing stances; incomplete boundary cycles are omitted.
    """
    samples = {}
    for side, joint in (("left", 6), ("right", 3)):
        down = np.sort(finite(events[f"{side}_down"]))
        up = np.sort(finite(events[f"{side}_up"]))
        peaks = []
        height = kp[:, joint, 1]
        for contact, next_contact in zip(down[:-1], down[1:]):
            offs = up[(up > contact) & (up < next_contact)]
            next_offs = up[up > next_contact]
            if len(offs) != 1 or not len(next_offs):
                continue
            off, next_off = offs[0], next_offs[0]
            if contact < 0 or next_off >= len(kp):
                continue
            # Central halves of stance avoid heel-strike/toe-off transitions.
            refs = []
            for a, b in ((contact, off), (next_contact, next_off)):
                frames = np.arange(int(np.ceil(a + .25 * (b - a))),
                                   int(np.floor(a + .75 * (b - a))) + 1)
                if not len(frames) or not np.all(np.isfinite(height[frames])):
                    break
                refs.append((float(frames.mean()), float(np.median(height[frames]))))
            if len(refs) != 2:
                continue
            swing = np.arange(int(np.floor(off)) + 1, int(np.ceil(next_contact)))
            if len(swing) < 2 or not np.all(np.isfinite(height[swing])):
                continue
            baseline = np.interp(swing, [r[0] for r in refs], [r[1] for r in refs])
            lift = float(np.max(height[swing] - baseline))
            # Negative peaks indicate an inconsistent baseline/track, not zero lift.
            if lift >= 0:
                peaks.append(lift * 1000.0)
        samples[f"ankle_lift_{side}"] = np.asarray(peaks)
    samples["frame_interval_ms"] = np.asarray([1000.0 / fps])
    return samples



def phase_time_samples(events, fps):
    """Retain phase durations without reporting their variability.

    Pair adjacent start/end events; incomplete or nonpositive intervals are
    unavailable without preventing the other gait features from being computed.
    Double support retains the historical sum of its two component intervals.
    """
    def intervals(starts, ends):
        ordered = sorted([(v, 0) for v in finite(starts)] + [(v, 1) for v in finite(ends)])
        values = [(b - a) / fps for (a, at), (b, bt) in zip(ordered[:-1], ordered[1:])
                  if at == 0 and bt == 1 and 0 < b - a <= 3 * fps]
        return np.asarray(values, dtype=float)
    result = {}
    for side in ("left", "right"):
        down, up = events[f"{side}_down"], events[f"{side}_up"]
        result[f"stance_{side}"] = intervals(down, up)
        result[f"swing_{side}"] = intervals(up, down)
    first = intervals(events["left_down"], events["right_up"])
    second = intervals(events["right_down"], events["left_up"])
    n = min(len(first), len(second))
    result["double_support"] = first[:n] + second[:n]
    return result


def extended_results(samples):
    """Summarize pooled event/sample arrays, balancing the two sides equally."""
    results = {}
    def bilateral(prefix, left, right, mean_label=None, temporal=False, report_variability=True):
        left, right = finite(left), finite(right)
        factor = 1000.0 if temporal else 1.0
        if left.size and right.size:
            if mean_label:
                results[mean_label] = float((left.mean() + right.mean()) / 2)
            results[f"{prefix} asymmetry" + (" (ms)" if temporal else "")] = float(
                abs(left.mean() - right.mean()) * factor)
        if not report_variability:
            return
        if left.size >= 2 and right.size >= 2:
            results[f"{prefix} variability" + (" (ms; estimated)" if temporal else "")] = float(
                np.sqrt((np.var(left, ddof=1) + np.var(right, ddof=1)) / 2) * factor)
        else:
            results[f"{prefix} variability" + (" (ms; estimated)" if temporal else "")] = float("nan")

    for prefix, key, label in (
        ("Step time", "step_time", "Average step time"),
    ):
        bilateral(prefix, samples.get(f"{key}_left", []), samples.get(f"{key}_right", []), label, True)
    for prefix, key, label in (
        ("Swing time", "swing", "Average swing time"),
        ("Stance time", "stance", "Average stance time"),
    ):
        if f"{key}_left" in samples or f"{key}_right" in samples:
            left, right = finite(samples.get(f"{key}_left", [])), finite(samples.get(f"{key}_right", []))
            bilateral(prefix, left, right, label, True, report_variability=False)
            results.setdefault(label, float("nan"))
            results[label + " left"] = float(left.mean()) if left.size else float("nan")
            results[label + " right"] = float(right.mean()) if right.size else float("nan")
    if "double_support" in samples:
        values = finite(samples["double_support"])
        results["Average double support time"] = float(values.mean()) if values.size else float("nan")
    if "Average step time" in results:
        results["Average cadence"] = 60.0 / results["Average step time"]
    for prefix, key, label in (
        ("Step length", "synthgait_step_length", "Average step length"),
        ("Step speed", "step_speed", "Average velocity"),
        ("Step width", "step_width", "Step width"),
    ):
        if f"{key}_left" in samples and f"{key}_right" in samples:
            bilateral(prefix, samples[f"{key}_left"], samples[f"{key}_right"], label)
            if key in ("synthgait_step_length", "step_speed"):
                for side in ("left", "right"):
                    values = finite(samples[f"{key}_{side}"])
                    results[label + " " + side] = float(values.mean()) if values.size else float("nan")
    for side in ("left", "right"):
        peaks = finite(samples.get(f"ankle_lift_{side}", []))
        if f"ankle_lift_{side}" in samples:
            results[f"Peak ankle lift {side} (mm; camera vertical)"] = float(peaks.mean()) if peaks.size else float("nan")
            results[f"Peak ankle lift valid swings {side}"] = int(peaks.size)
        speeds = np.abs(finite(samples.get(f"arm_velocity_{side}", [])))
        if speeds.size:
            results[f"Arm swing mean speed {side} (m/s)"] = float(speeds.mean())
            results[f"Arm swing P95 speed {side} (m/s)"] = float(np.percentile(speeds, 95))
    for metric in ("Peak ankle lift", "Arm swing mean speed", "Arm swing P95 speed"):
        suffix = " (mm; camera vertical)" if metric == "Peak ankle lift" else " (m/s)"
        keys = [f"{metric} {side}{suffix}" for side in ("left", "right")]
        if all(key in results for key in keys):
            results[metric + suffix] = float(np.mean([results[key] for key in keys]))
    trunk_velocity = finite(samples.get("torso_ml_velocity", []))
    if trunk_velocity.size:
        results["Torso medial-lateral mean speed (m/s)"] = float(np.mean(np.abs(trunk_velocity)))
        results["Torso medial-lateral P95 speed (m/s)"] = float(np.percentile(np.abs(trunk_velocity), 95))
    intervals = finite(samples.get("frame_interval_ms", []))
    if intervals.size:
        results["Video frame interval (ms)"] = float(np.max(intervals))
        results["Temporal variability interpretation"] = "Estimated; video event timing limits precision"
    return results
