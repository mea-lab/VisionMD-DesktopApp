"""Hierarchical equal-weight combination of bilateral, within-segment variances."""
import numpy as np


def combine_segment_variability(segments, minimum_per_side=5):
    """sqrt(mean_segment((var_left + var_right)/2)); no segment-size weighting."""
    segment_variances, counts, segment_counts = [], {"left": 0, "right": 0}, []
    for segment in segments:
        sides = {s: np.asarray(segment.get(s, []), float) for s in counts}
        sides = {s: v[np.isfinite(v)] for s, v in sides.items()}
        if any(len(v) < 2 for v in sides.values()):
            continue
        segment_variances.append(float(np.mean([np.var(v, ddof=1) for v in sides.values()])))
        segment_counts.append({s: int(len(v)) for s, v in sides.items()})
        for side in counts:
            counts[side] += len(sides[side])
    available = bool(segment_variances) and min(counts.values()) >= minimum_per_side
    return {"value": float(np.sqrt(np.mean(segment_variances))) if available else None,
            "available": bool(available), "samples_per_side": counts,
            "segment_sample_counts": segment_counts,
            "segment_sds": [float(np.sqrt(v)) for v in segment_variances],
            "segments_used": len(segment_variances),
            "method": "equal-weight mean of segment variances, each segment variance is the equal-side mean of sample variances"}
