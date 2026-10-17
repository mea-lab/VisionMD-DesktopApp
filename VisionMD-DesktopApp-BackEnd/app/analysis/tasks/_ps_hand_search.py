"""Image-space safeguards for participant-associated P/S hand localization."""
from __future__ import annotations

import numpy as np

PS_SEARCH_VERSION = "ps-expanded-search-v1"


def expanded_search_box(subject, width, height, padding):
    """Pad the subject selection; clip only at the actual image boundary."""
    x, y = float(subject['x']), float(subject['y'])
    w, h = float(subject['width']), float(subject['height'])
    if w <= 0 or h <= 0 or x >= width or y >= height or x + w <= 0 or y + h <= 0:
        raise ValueError('The selected subject bounding box is outside the video frame.')
    return np.array([max(0, int(np.floor(x-padding*w))),
                     max(0, int(np.floor(y-padding*h))),
                     min(width, int(np.ceil(x+(1+padding)*w))),
                     min(height, int(np.ceil(y+(1+padding)*h)))])


def associated_boxes(boxes, subject):
    """Keep hands near the selected participant, including extended arms.

    This limits an expanded search to a participant-sized reach envelope.
    Handedness filtering and one-to-one temporal association are applied by
    the caller; this envelope alone is not a proof of participant identity.
    """
    boxes = np.asarray(boxes, float).reshape(-1, 4)
    x, y = subject['x'], subject['y']
    w, h = subject['width'], subject['height']
    centers = (boxes[:, :2] + boxes[:, 2:]) / 2
    keep = ((centers[:, 0] >= x-.5*w) & (centers[:, 0] <= x+1.5*w)
            & (centers[:, 1] >= y-.5*h) & (centers[:, 1] <= y+1.5*h))
    return boxes[keep]


def track_search_quality(track, count, step, fps, search_box, width, height):
    """Measure observed coverage, longest unsupported gap, and crop clipping.

    Frames filled by ROI interpolation never count as observed detections.
    Only artificial search edges count as clipping, not the image boundary.
    """
    expected = np.arange(0, count, step)
    times = np.array([i for i, _ in track], dtype=int)
    observed = np.isin(expected, times)
    coverage = float(observed.mean()) if len(observed) else 0.
    longest = run = 0
    for present in observed:
        run = 0 if present else run + 1
        longest = max(longest, run)
    gap_s = min(count, longest * step) / fps
    clipped = 0
    for _, box in track:
        size = max(box[2]-box[0], box[3]-box[1], 1.)
        margin = .10 * size
        clipped += bool((search_box[0] > 0 and box[0]-search_box[0] < margin)
                        or (search_box[1] > 0 and box[1]-search_box[1] < margin)
                        or (search_box[2] < width and search_box[2]-box[2] < margin)
                        or (search_box[3] < height and search_box[3]-box[3] < margin))
    edge_fraction = clipped / max(1, len(track))
    reasons = []
    if coverage < .80: reasons.append('Hand localization coverage below 80%')
    if gap_s > .50: reasons.append('Hand localization gap longer than 0.5 seconds')
    if edge_fraction > .05: reasons.append('Hand detections touch the search boundary')
    return {'pass': not reasons, 'coverage': coverage, 'max_gap_seconds': float(gap_s),
            'boundary_fraction': float(edge_fraction), 'reasons': reasons}
