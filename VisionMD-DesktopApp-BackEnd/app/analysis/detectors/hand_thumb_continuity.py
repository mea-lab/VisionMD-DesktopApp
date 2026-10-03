"""Conservative thumb-tip jump checks in hand-relative coordinates."""
import numpy as np


def thumb_identity_jump_mask(values, palm, fps=30.0, max_run_seconds=0.12):
    """Flag abrupt anatomically inconsistent thumb excursions.

    Thumb/index contact is legitimate. Being near another finger alone is not
    an error: an excursion must also depart abruptly from the wrist-relative
    trajectory. Only bounded short runs can later be interpolated.
    """
    xy = np.asarray(values, dtype=float)[:, :, :2]
    scale = np.maximum(np.asarray(palm, dtype=float), 1e-6)
    relative = (xy[:, 4] - xy[:, 0]) / scale[:, None]
    own = np.linalg.norm(xy[:, 4] - xy[:, 3], axis=1) / scale
    others = np.min(np.linalg.norm(xy[:, 4, None] - xy[:, [7, 11, 15, 19]], axis=2), axis=1) / scale
    median_bone = np.nanmedian(own)
    anatomical = (own > max(0.50, 2.5 * median_bone)) | (own - others > 0.15)
    # The thumb MCP is attached to the hand: a large isolated MCP excursion
    # while the other MCPs remain stable implicates the whole thumb branch.
    hand_relative = (xy - xy[:, [0]]) / scale[:, None, None]
    branch_spikes = np.zeros(len(xy), dtype=bool)
    if len(xy) >= 3:
        midpoint = (hand_relative[:-2] + hand_relative[2:]) / 2
        residuals = np.linalg.norm(hand_relative[1:-1] - midpoint, axis=2)
        branch_spikes[1:-1] = (
            (residuals[:, 2] > 0.50) & (residuals[:, 4] > 0.75)
            & (np.linalg.norm(hand_relative[1:-1, 2] - hand_relative[:-2, 2], axis=1) > 0.50)
            & (np.linalg.norm(hand_relative[1:-1, 2] - hand_relative[2:, 2], axis=1) > 0.50)
            & (np.median(residuals[:, [5, 9, 13, 17]], axis=1) < 0.50)
            # During rapid whole-hand repositioning the thumb branch can
            # legitimately rotate. Leave this ambiguous motion untouched.
            & (np.linalg.norm(xy[2:, 0] - xy[:-2, 0], axis=1) / scale[1:-1] < 0.25)
        )
    anatomical |= branch_spikes
    mask = np.zeros(len(xy), dtype=bool)
    max_run = max(1, int(round(float(fps or 30.0) * max_run_seconds)))
    indices = np.flatnonzero(anatomical)
    for run in np.split(indices, np.where(np.diff(indices) > 1)[0] + 1):
        if not len(run):
            continue
        left, right = int(run[0]) - 1, int(run[-1]) + 1
        if left < 0 or right >= len(xy):
            # A one-sided estimate cannot establish a return to the trajectory.
            # Flag gross bone elongation only; never interpolate an edge run.
            mask[run] = own[run] > max(0.50, 2.5 * median_bone)
            continue
        if len(run) <= max_run:
            weight = ((run - left) / (right - left))[:, None]
            expected = relative[left] * (1 - weight) + relative[right] * weight
            residual = np.linalg.norm(relative[run] - expected, axis=1)
            anchors = np.linalg.norm(relative[right] - relative[left])
            if np.max(residual) > 0.35 and anchors <= 0.50:
                mask[run] = True
        else:
            incoming = np.linalg.norm(relative[run[0]] - relative[left])
            outgoing = np.linalg.norm(relative[right] - relative[run[-1]])
            if max(incoming, outgoing) > 0.35:
                mask[run] = True
    return mask, branch_spikes
