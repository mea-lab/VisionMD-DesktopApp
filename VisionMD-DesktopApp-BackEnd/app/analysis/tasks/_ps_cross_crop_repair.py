"""Verify a persistent 360-degree offset against an independently inferred crop.

This changes angles only. Accepted corrections remain provisional and require
visual review; a plausible waveform is not a calibrated anatomical measurement.
"""
import numpy as np
from scipy.ndimage import median_filter


def repair_cross_crop_branch(original, reference, fps):
    angle = np.asarray(original, float)
    reference = np.asarray(reference, float).copy()
    diagnostics = {"attempted": True, "accepted": False,
                   "reason": "insufficient_evidence", "events": []}

    def reject(reason):
        return angle.copy(), dict(diagnostics, reason=reason)

    if not np.isfinite(fps) or fps <= 0:
        return reject("invalid_fps")
    if (angle.ndim != 1 or reference.ndim != 1 or len(reference) != len(angle)
            or len(angle) < 4 * fps or not np.isfinite(angle).all()
            or not np.isfinite(reference).all()):
        return reject("insufficient_or_invalid_data")

    count = len(angle)
    original_range = float(np.ptp(np.percentile(angle, [5, 95])))
    reference_range = float(np.ptp(np.percentile(reference, [5, 95])))
    if original_range <= 250 or reference_range > 250:
        return reject("no_supported_excessive_range")

    anchor = round(2.5 * fps)
    reference += np.median(angle[:anchor] - reference[:anchor])
    offset = angle - reference
    if np.percentile(abs(offset[:anchor]), 90) > 35:
        return reject("crops_disagree_at_anchor")
    states = median_filter(np.rint(offset / 360).astype(int),
                           size=max(3, round(.25 * fps) | 1), mode="nearest")
    if np.any(states[:anchor] != 0):
        return reject("unsupported_initial_branch")
    changes = np.flatnonzero(np.diff(states) != 0) + 1
    changes = changes[changes >= anchor]
    if len(changes) != 1:
        return reject("ambiguous_or_multiple_changes")

    cut = int(changes[0])
    old, new = int(states[cut - 1]), int(states[cut])
    valid = abs(offset - 360 * states) < 35
    if old != 0 or abs(new) != 1:
        return reject("unsupported_branch_offset")
    for lo, hi, state in [(max(anchor, cut-round(fps)), cut, old),
                          (cut, min(count, cut+round(fps)), new)]:
        supported = valid[lo:hi] & (states[lo:hi] == state)
        if supported.sum() < .6 * fps:
            return reject("insufficient_sustained_crop_agreement")

    proposal = angle - 360 * states
    # Use new observations only around the inconsistent transition. Preserve
    # the measured waveform elsewhere, allowing only the constant branch shift.
    inconsistent = abs(proposal-reference) > 35
    lo = hi = cut
    while lo > 0 and (inconsistent[lo-1] or lo == cut):
        lo -= 1
    while hi < count-1 and (inconsistent[hi+1] or hi == cut):
        hi += 1
    lo, hi = max(0, lo-1), min(count-1, hi+1)
    if hi-lo > .5 * fps:
        return reject("transition_too_long")
    endpoint_offset = np.linspace(proposal[lo]-reference[lo],
                                  proposal[hi]-reference[hi], hi-lo+1)
    proposal[lo:hi+1] = reference[lo:hi+1] + endpoint_offset

    repaired_range = float(np.ptp(np.percentile(proposal, [5, 95])))
    if repaired_range > 250 or repaired_range < .3 * original_range:
        return reject("implausible_repaired_range")
    if max(abs(np.diff(proposal))) > 1.1 * max(60., max(abs(np.diff(angle)))):
        return reject("worsened_steps")
    diagnostics.update(
        accepted=True, reason="persistent_cross_crop_supported_winding",
        events=[{"cut_frame": cut, "suffix_offset_deg": -360*new,
                 "replacement_interval_frames": [lo, hi],
                 "replacement_duration_s": (hi-lo)/fps}],
        original_robust_range_deg=original_range,
        repaired_robust_range_deg=repaired_range,
        requires_visual_verification=True,
    )
    return proposal, diagnostics
