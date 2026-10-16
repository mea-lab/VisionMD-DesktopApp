"""Confirm orientation transitions using movement outside the rotation.

Depth is in millimetres. Returned intervals are inclusive and include a
one-second guard on either side to exclude transition steps from steady gait.
"""
import numpy as np
from scipy.ndimage import median_filter


def confirmed_turn_intervals(depth, yaw, fps, minimum_turn_degrees=75.0,
                             box_heights=None):
    depth = np.asarray(depth, dtype=float)
    yaw = np.asarray(yaw, dtype=float)
    if (not np.isfinite(fps) or fps <= 0 or depth.ndim != 1 or
            yaw.shape != depth.shape or len(depth) < 5):
        return []
    valid = np.isfinite(depth)
    if valid.sum() < max(5, int(fps)) or not np.all(np.isfinite(yaw)):
        return []
    depth = np.interp(np.arange(len(depth)), np.flatnonzero(valid), depth[valid])
    window = max(3, int(round(.5 * fps)) | 1)
    smooth = median_filter(depth, size=window, mode="nearest")
    noise = 1.4826 * np.median(np.abs(depth - smooth))
    excursion = max(100.0, 4 * noise)
    sizes = None
    if box_heights is not None:
        sizes = np.asarray(box_heights, dtype=float)
        if (sizes.shape != depth.shape or not np.all(np.isfinite(sizes)) or
                np.any(sizes <= 0)):
            return []
        # Fixed user-drawn crops provide no direction evidence.
        if np.ptp(sizes) / np.median(sizes) < .1:
            sizes = None
        else:
            sizes = median_filter(sizes, size=window, mode="nearest")

    radius = max(2, int(round(3 * fps)))
    plateau = max(2, int(round(.5 * fps)))
    candidates = []
    for center in range(plateau, len(depth) - plateau,
                        max(1, int(round(.1 * fps)))):
        a, b = max(0, center - radius), min(len(depth), center + radius + 1)
        initial = np.median(yaw[a:a + plateau])
        final = np.median(yaw[b - plateau:b])
        delta = final - initial
        if not minimum_turn_degrees <= abs(np.degrees(delta)) <= 270:
            continue
        progress = (yaw[a:b] - initial) * np.sign(delta)
        middle = np.flatnonzero(progress >= .5 * abs(delta))
        if not len(middle):
            continue
        m = int(middle[0])
        starts = np.flatnonzero(progress[:m] <= .05 * abs(delta))
        ends = np.flatnonzero(progress[m + 1:] >= .95 * abs(delta))
        if not len(starts) or not len(ends):
            continue
        start = a + int(starts[-1])
        end = a + m + 1 + int(ends[0])
        if end - start > 4 * fps or end - start < .15 * fps:
            continue
        # The 3D pelvis estimate can develop a double peak during rotation.
        # Confirm approach/departure outside the complete orientation interval.
        before_start = max(0, start - radius)
        after_end = min(len(depth), end + 1 + radius)
        before, after = smooth[before_start:start], smooth[end + 1:after_end]
        if len(before) < fps or len(after) < fps:
            continue
        left_change = np.median(before[-plateau:]) - np.median(before[:plateau])
        right_change = np.median(after[-plateau:]) - np.median(after[:plateau])
        for sign in (1, -1):
            if sign * left_change < excursion or sign * right_change > -excursion:
                continue
            if (np.mean(sign * np.diff(before) >= -noise) < .7 or
                    np.mean(sign * np.diff(after) <= noise) < .7):
                continue
            if sizes is not None:
                size_before = sizes[before_start:start]
                size_after = sizes[end + 1:after_end]
                size_left = (np.median(size_before[-plateau:]) -
                             np.median(size_before[:plateau]))
                size_right = (np.median(size_after[-plateau:]) -
                              np.median(size_after[:plateau]))
                threshold = .02 * np.median(sizes[start:end + 1])
                # Sustained size change in the same direction on both sides
                # contradicts a turnaround. Small changes are inconclusive.
                if ((size_left > threshold and size_right > threshold) or
                        (size_left < -threshold and size_right < -threshold)):
                    continue
            candidates.append((start, end, a + m,
                               min(sign * left_change, -sign * right_change)))

    # Adjacent windows can describe different parts of the same rotation.
    merged = []
    for start, end, center, strength in sorted(candidates):
        if merged and start <= merged[-1][1] + fps:
            previous = merged.pop()
            merged.append((previous[0], max(previous[1], end),
                           center if strength > previous[3] else previous[2],
                           max(previous[3], strength)))
        else:
            merged.append((start, end, center, strength))
    guard = max(1, int(round(fps)))
    return [(max(0, start - guard), min(len(depth) - 1, end + guard), center, strength)
            for start, end, center, strength in merged]
