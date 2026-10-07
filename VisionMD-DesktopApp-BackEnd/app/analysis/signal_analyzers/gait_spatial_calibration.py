"""Participant-height calibration for MeTRAbs gait distance estimates."""

from __future__ import annotations

import numpy as np


# Fitted through the origin after participant-level averaging in the wearable
# validation cohort (35 participants; Val_005 excluded). Leave-one-participant-
# out validation selected straight stature over leg and articulated-chain
# proxies. Keep this value versioned so historical analyses remain reproducible.
HEIGHT_CALIBRATION_COEFFICIENT = 0.8527967929746464
HEIGHT_CALIBRATION_VERSION = "noraxon-height-stature-v1"


def height_spatial_calibration(poses_mm, height_cm):
    """Return the validated spatial scale and its audit metadata.

    ``poses_mm`` must use the 17-joint ``mpi_inf_3dhp_17`` order. The skeletal
    proxy is the median, across frames, of the mean 3D distance from head-top
    to the two ankles. It is calculated from the original inference pass and
    the resulting factor is shared with the mirrored pass.
    """
    poses = np.asarray(poses_mm, dtype=float)
    height_m = float(height_cm) / 100.0
    if poses.ndim != 3 or poses.shape[1] < 14 or poses.shape[2] != 3:
        raise ValueError("Height calibration requires mpi_inf_3dhp_17 3D poses.")
    if not np.isfinite(height_m) or height_m <= 0:
        raise ValueError("Height calibration requires a positive finite participant height.")

    right = np.linalg.norm(poses[:, 0] - poses[:, 10], axis=1) / 1000.0
    left = np.linalg.norm(poses[:, 0] - poses[:, 13], axis=1) / 1000.0
    per_frame_stature = (right + left) / 2.0
    valid = per_frame_stature[np.isfinite(per_frame_stature) & (per_frame_stature > 0)]
    if not valid.size:
        raise ValueError("Height calibration could not estimate MeTRAbs stature.")

    model_stature_m = float(np.median(valid))
    scale_factor = HEIGHT_CALIBRATION_COEFFICIENT * height_m / model_stature_m
    if not np.isfinite(scale_factor) or scale_factor <= 0:
        raise ValueError("Height calibration produced an invalid spatial scale.")

    return {
        "version": HEIGHT_CALIBRATION_VERSION,
        "method": "coefficient * measured height / median MeTRAbs head-to-ankle stature",
        "coefficient": HEIGHT_CALIBRATION_COEFFICIENT,
        "participant_height_m": height_m,
        "model_straight_stature_m": model_stature_m,
        "scale_factor": float(scale_factor),
        "source_pose_pass": "original",
        "applied_to": ["step_length", "step_speed"],
    }
