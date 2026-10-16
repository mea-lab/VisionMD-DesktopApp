"""Full-person eligibility for gait; unknown visibility is never filled in."""
import numpy as np


def full_person_visible(keypoints, box, width, height, confidence=.25):
    """COCO head landmarks + both ankles, with space for head/feet at edges."""
    if keypoints is None:
        return False
    points = np.asarray(keypoints, dtype=float)
    box = np.asarray(box, dtype=float)
    if points.shape != (17, 3) or box.shape != (4,) or not np.isfinite(points).all() or not np.isfinite(box).all():
        return False
    mx, my = .01 * width, .01 * height
    if box[0] <= mx or box[1] <= my or box[2] >= width-mx or box[3] >= height-my:
        return False
    inside = ((points[:, 0] > mx) & (points[:, 0] < width-mx)
              & (points[:, 1] > my) & (points[:, 1] < height-my))
    heads = np.flatnonzero((points[:5, 2] > confidence) & inside[:5])
    if not heads.size or not np.all((points[[15, 16], 2] > confidence) & inside[[15, 16]]):
        return False
    # A visible nose alone does not establish that the top of the head is in
    # frame. Likewise leave a shoe margin below the ankle landmark.
    shoulders = points[[5, 6], :2].mean(axis=0)
    head = points[heads, :2].mean(axis=0)
    if head[1] - .5 * np.linalg.norm(shoulders-head) <= my:
        return False
    for knee, ankle in ((13, 15), (14, 16)):
        shoe_margin = .25 * np.linalg.norm(points[knee, :2]-points[ankle, :2])
        if points[ankle, 1] + shoe_margin >= height-my:
            return False
    return True


def visible_ranges(mask):
    """Half-open continuous intervals; even one ineligible frame splits a run."""
    mask = np.asarray(mask, dtype=bool).reshape(-1)
    edges = np.diff(np.r_[False, mask, False].astype(int))
    return [[int(a), int(b)] for a, b in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1))]


def restrict_walking_ranges(walking_ranges, visibility, frame_count):
    """Intersect straight walking with certified full-person ranges."""
    if visibility is None:
        return walking_ranges
    allowed = visibility.get('frame_ranges')
    if not isinstance(allowed, list):
        raise ValueError('Full-person visibility requires frame_ranges.')
    previous = 0
    for interval in allowed:
        if (not isinstance(interval, (list, tuple)) or len(interval) != 2
                or any(isinstance(v, bool) or not isinstance(v, int) for v in interval)):
            raise ValueError('Visibility intervals must have integer start/end frames.')
        a, b = interval
        if not 0 <= a < b <= frame_count or a < previous:
            raise ValueError('Visibility intervals must be ordered, disjoint and inside the video.')
        previous = b
    return [(max(a, c), min(b, d)) for a, b in walking_ranges for c, d in allowed if max(a, c) < min(b, d)]
