"""Conservative camera-depth turn confirmation (MeTRAbs distances in mm)."""
import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import find_peaks


def confirmed_turn_intervals(depth, yaw, fps, minimum_turn_degrees=75.0):
    depth = np.asarray(depth, dtype=float)
    yaw = np.asarray(yaw, dtype=float)
    if not np.isfinite(fps) or fps <= 0 or len(depth) != len(yaw):
        return []
    valid = np.isfinite(depth)
    if valid.sum() < max(5, int(fps)) or not np.all(np.isfinite(yaw)):
        return []
    depth = np.interp(np.arange(len(depth)), np.flatnonzero(valid), depth[valid])
    window = max(3, int(round(.5 * fps)) | 1)
    smooth = median_filter(depth, size=window, mode="nearest")
    noise = 1.4826 * np.median(np.abs(depth - smooth))
    excursion = max(100.0, 4 * noise)
    radius = max(2, int(round(3 * fps)))
    plateau = max(2, int(round(.5 * fps)))
    candidates = []
    for sign in (1, -1):
        peaks, _ = find_peaks(sign * smooth, prominence=excursion,
                             distance=max(1, int(fps)))
        for center in peaks:
            a, b = max(0, center-radius), min(len(depth), center+radius+1)
            before, after = smooth[a:center-plateau], smooth[center+plateau:b]
            if len(before) < fps or len(after) < fps:
                continue
            # A peak needs sustained approach and departure, rather than jitter.
            left_change = sign * (np.median(before[-plateau:]) - np.median(before[:plateau]))
            right_change = sign * (np.median(after[-plateau:]) - np.median(after[:plateau]))
            left_steps, right_steps = sign*np.diff(before), sign*np.diff(after)
            if left_change < excursion or right_change > -excursion:
                continue
            if np.mean(left_steps >= -noise) < .7 or np.mean(right_steps <= noise) < .7:
                continue
            initial, final = np.median(yaw[a:a+plateau]), np.median(yaw[b-plateau:b])
            delta = final-initial
            if not minimum_turn_degrees <= abs(np.degrees(delta)) <= 270:
                continue
            progress = (yaw[a:b]-initial)*np.sign(delta)
            middle = np.flatnonzero(progress >= .5*abs(delta))
            if not len(middle):
                continue
            m = int(middle[0])
            starts = np.flatnonzero(progress[:m] <= .05*abs(delta))
            ends = np.flatnonzero(progress[m+1:] >= .95*abs(delta))
            if not len(starts) or not len(ends):
                continue
            start, end = a+int(starts[-1]), a+m+1+int(ends[0])
            if not start <= center <= end:
                continue
            candidates.append((start, end, int(center), min(left_change, -right_change)))
    return candidates
