"""Opposite-foot progression-line geometry using estimated ankle contacts."""
import numpy as np
from app.analysis.signal_analyzers.gait_segment_variability import combine_segment_variability
from app.analysis.signal_analyzers.gait_steady_step import BOUNDARY_SECONDS, MIN_SAMPLES_PER_SIDE

POOLED_FEATURE = "Steady-step width SD (m; estimated)"
WITHIN_FEATURE = "Steady-step width within-segment SD (m; estimated)"
STEADY_WIDTH_FEATURES = (POOLED_FEATURE, WITHIN_FEATURE)


def foot_line_widths(left_frames, left_points, right_frames, right_points):
    """Middle contact distance to the line through its bracketing opposite contacts.

    Points are in metres, in the estimated horizontal camera-XZ plane.
    Left/right side indices 6/3 match the gait-phase joint order.
    """
    contacts = sorted([(int(f), 6, np.asarray(p, float)) for f, p in zip(left_frames, left_points)]
                      + [(int(f), 3, np.asarray(p, float)) for f, p in zip(right_frames, right_points)], key=lambda c: c[0])
    widths, sides, frames = [], [], []
    for a, p, b in zip(contacts[:-2], contacts[1:-1], contacts[2:]):
        if not a[0] < p[0] < b[0] or a[1] != b[1] or a[1] == p[1]:
            continue
        if not np.isfinite(np.array([a[2], p[2], b[2]])).all():
            continue
        v, u = b[2] - a[2], p[2] - a[2]
        norm = float(np.linalg.norm(v))
        if norm <= 1e-6:
            continue
        widths.append(abs(float(v[0] * u[1] - v[1] * u[0])) / norm)
        sides.append(p[1]);frames.append(p[0])
    return {"widths": np.asarray(widths, float), "sides": np.asarray(sides, int), "frames": np.asarray(frames, int)}


def steady_width_samples(events, poses_mm, fps):
    """All three contacts must lie inside the fixed two-second central window."""
    fps = float(fps)
    if not np.isfinite(fps) or fps <= 0:
        raise ValueError("Steady-step width requires positive finite FPS.")
    poses = np.asarray(poses_mm, float)
    lo, hi = BOUNDARY_SECONDS * fps, len(poses) - BOUNDARY_SECONDS * fps
    contacts = {}
    for side, joint in (("left", 13), ("right", 10)):
        values = np.asarray(events.get(side + "_down", []), float)
        values = values[np.isfinite(values) & (values >= lo) & (values < hi)]
        frames = np.round(values).astype(int)
        frames = frames[(frames >= 0) & (frames < len(poses))]
        contacts[side] = (frames, poses[frames, joint][:, [0, 2]] / 1000.)
    widths = foot_line_widths(*contacts["left"], *contacts["right"])
    return {side: widths["widths"][widths["sides"] == index] for side, index in (("left", 6), ("right", 3))}


def summarize_width(segments):
    """One reported SD: equal-weight combination of segment-side variances."""
    stats = combine_segment_variability(segments, MIN_SAMPLES_PER_SIDE)
    pooled = []
    for side in ("left", "right"):
        arrays = [np.asarray(s.get(side, []), float) for s in segments]
        values = np.concatenate(arrays) if arrays else np.array([])
        values = values[np.isfinite(values)]
        pooled.append(float(np.var(values, ddof=1)) if len(values) >= 2 else np.nan)
    stats["within_segment_sd_m"] = stats.pop("value")
    stats["segment_sds_m"] = stats.pop("segment_sds")
    stats["pooled_sd_m"] = float(np.sqrt(np.mean(pooled))) if stats["available"] else None
    return stats
