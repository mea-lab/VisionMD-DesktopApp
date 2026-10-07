"""Steady-step time SD: fixed central windows and within-segment residual variance."""
import numpy as np
from app.analysis.signal_analyzers.gait_segment_variability import combine_segment_variability

FEATURE_NAME = "Steady-step gait time SD (ms)"
BOUNDARY_SECONDS = 2.0
MIN_SAMPLES_PER_SIDE = 5
UNAVAILABLE = "Not available: insufficient steady steps"


def segment_step_times(events, frame_count, fps):
    """Keep complete step intervals inside [2 seconds, duration - 2 seconds)."""
    fps = float(fps)
    if not np.isfinite(fps) or fps <= 0:
        raise ValueError("Steady-step gait requires positive finite FPS.")
    lo, hi = BOUNDARY_SECONDS * fps, frame_count - BOUNDARY_SECONDS * fps
    samples = {"left": np.asarray([], dtype=float), "right": np.asarray([], dtype=float)}
    if hi <= lo:
        return samples
    strikes = {}
    for side in samples:
        values = np.asarray(events.get(side + "_down", []), dtype=float)
        strikes[side] = np.sort(values[np.isfinite(values) & (values >= lo) & (values < hi)])
    ordered = sorted((frame, side) for side, values in strikes.items() for frame in values)
    # A missing/repeated-side event makes its two adjacent intervals ambiguous.
    # Do not let pairing by array index convert it into a long apparent step.
    for side in samples:
        values = [(b[0] - a[0]) / fps for a, b in zip(ordered[:-1], ordered[1:])
                  if a[1] != b[1] and b[1] == side and 0 < b[0] - a[0] <= 3 * fps]
        samples[side] = np.asarray(values, dtype=float)
    return samples


def summarize_step_times(segments):
    """Equal-weight segment variance combination, converted to milliseconds."""
    stats = combine_segment_variability(segments, MIN_SAMPLES_PER_SIDE)
    value = stats.pop("value")
    stats["value_ms"] = value * 1000 if value is not None else None
    stats["segment_sds_ms"] = [v * 1000 for v in stats.pop("segment_sds")]
    return stats


def segment_ankle_length_speed(events, poses_mm, fps, spatial_scale=1.0):
    """Diagnostic spatial samples inside the same two-second steady windows."""
    poses = np.asarray(poses_mm, float);fps = float(fps)
    lo, hi = BOUNDARY_SECONDS * fps, len(poses) - BOUNDARY_SECONDS * fps
    out = {metric: {"left": [], "right": []} for metric in ("length", "speed")}
    contacts = sorted((int(round(f)), side) for side in ("left", "right")
                      for f in events.get(side + "_down", []) if np.isfinite(f) and lo <= f < hi)
    if len(contacts) < 2:
        return out
    travel = poses[contacts[-1][0], 14, [0, 2]] - poses[contacts[0][0], 14, [0, 2]]
    norm = float(np.linalg.norm(travel))
    if not np.isfinite(norm) or norm < 1e-6:
        return out
    forward = travel / norm
    for (af, aside), (bf, bside) in zip(contacts[:-1], contacts[1:]):
        if af >= bf or aside == bside:
            continue
        a = poses[af, 13 if aside == "left" else 10, [0, 2]] / 1000
        b = poses[bf, 13 if bside == "left" else 10, [0, 2]] / 1000
        length = abs(float((b - a) @ forward)) * float(spatial_scale)
        out["length"][bside].append(length)
        out["speed"][bside].append(length / ((bf - af) / fps))
    return out
