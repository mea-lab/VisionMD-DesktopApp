"""Validated temporal algorithms used by VisionMD P/S analysis.

This module is intentionally independent of Django.  It contains the same
hand-track association, batched WiLoR inference, landmark branch decoder,
angle diagnostics/repairs, and zero-phase low-pass filter used by the
standalone validation pipeline.  VisionMD-specific request and response logic
lives in ``_pronation_supination.py``.

The functions are kept together because their thresholds were validated as a
sequence.  In particular, landmark branch decoding precedes angle repair;
reordering those operations changes the result.
"""
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
from scipy.signal import butter, sosfiltfilt
from skimage.filters import gaussian
from app.analysis.torch_device import run_with_device_fallback


def file_sha256(path: str | Path) -> str:
    """Return a stable source-video identifier for result provenance."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass
class Detection:
    frame: int
    box: np.ndarray  # x1, y1, x2, y2
    center: np.ndarray


def square_roi(boxes: list[np.ndarray], width: int, height: int, scale: float) -> np.ndarray:
    """Robust 5th/95th percentile ROI, made square and clipped to the frame."""
    data = np.asarray(boxes, dtype=float)
    x1, y1 = np.percentile(data[:, :2], 5, axis=0)
    x2, y2 = np.percentile(data[:, 2:], 95, axis=0)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    side = max(x2 - x1, y2 - y1) * scale
    return np.array([max(0, cx - side / 2), max(0, cy - side / 2),
                     min(width - 1, cx + side / 2), min(height - 1, cy + side / 2)])


def select_moving_track_timed(samples: dict[int, list[np.ndarray]]) -> list[tuple[int, np.ndarray]]:
    """Associate detections one-to-one, then select the sustained, mobile hand track.

    A track can receive at most one detection per localization frame.  This is
    essential: the old greedy loop allowed both hands to attach to the same
    track, producing an ROI that spanned the person's entire torso.
    """
    tracks: list[list[tuple[int, np.ndarray]]] = []
    for frame_idx, boxes in sorted(samples.items()):
        boxes = [np.asarray(b, dtype=float) for b in boxes]
        if not tracks:
            tracks = [[(frame_idx, b)] for b in boxes]
            continue
        candidates = []
        for ti, track in enumerate(tracks):
            prior = track[-1][1]
            prior_center = (prior[:2] + prior[2:]) / 2
            prior_size = max(prior[2] - prior[0], prior[3] - prior[1])
            for bi, box in enumerate(boxes):
                center = (box[:2] + box[2:]) / 2
                size = max(box[2] - box[0], box[3] - box[1])
                distance = np.linalg.norm(center - prior_center)
                # Reject identity jumps rather than letting a left/right hand
                # or a bystander's hand become part of this track.
                if distance <= max(70.0, 2.5 * prior_size) and 0.4 <= size / max(prior_size, 1) <= 2.5:
                    candidates.append((distance / max(prior_size, 1), ti, bi))
        used_tracks, used_boxes = set(), set()
        for _, ti, bi in sorted(candidates):
            if ti not in used_tracks and bi not in used_boxes:
                tracks[ti].append((frame_idx, boxes[bi])); used_tracks.add(ti); used_boxes.add(bi)
        # Retain unmatched hands as separate tracks; later coverage filtering
        # removes transient false positives and bystander detections.
        tracks.extend([[(frame_idx, box)] for bi, box in enumerate(boxes) if bi not in used_boxes])
    if not tracks:
        raise RuntimeError("No hands were localised. Inspect the video/crop and detector settings.")
    def score(track: list[tuple[int, np.ndarray]]) -> float:
        if len(track) < max(3, int(len(samples) * .5)): return -np.inf
        c = np.array([(b[:2] + b[2:]) / 2 for _, b in track])
        size = np.median([max(b[2] - b[0], b[3] - b[1]) for _, b in track])
        return float(np.linalg.norm(np.diff(c, axis=0), axis=1).sum() / max(size, 1))
    selected = max(tracks, key=score)
    if not np.isfinite(score(selected)):
        raise RuntimeError("No hand track persisted through enough localization frames.")
    return selected


def select_moving_track(samples: dict[int, list[np.ndarray]]) -> list[np.ndarray]:
    """Compatibility wrapper returning boxes only."""
    return [box for _, box in select_moving_track_timed(samples)]


def screen_hand_track(video: str, detector, localization_fps: float) -> dict:
    """Cheaply measure whether one hand is sustained in a video/candidate ROI.

    ``detector`` may already crop to a static person candidate.  The result is
    deliberately 2-D only: it is for ranking candidates before WiLoR runs.
    """
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        raise FileNotFoundError(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, round(fps / localization_fps))
    samples: dict[int, list[np.ndarray]] = {}
    sampled = 0
    frame_id = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_id % step == 0:
            sampled += 1
            boxes = detector(frame)
            if boxes:
                samples[frame_id] = boxes
        frame_id += 1
    cap.release()
    result = {"sampled_frames": sampled, "frames_with_hand": len(samples),
              "hand_coverage": len(samples) / max(1, sampled), "track_frames": 0,
              "track_coverage": 0.0}
    try:
        track = select_moving_track_timed(samples)
    except RuntimeError:
        return result
    result["track_frames"] = len(track)
    result["track_coverage"] = len(track) / max(1, sampled)
    return result


class WiLorBatch:
    """Uses WiLoR's underlying model directly so frames can be stacked in batches."""
    def __init__(self, device: str, pretrained_dir: str | None = None):
        from app.analysis.models.wilor_mini.pipelines.wilor_hand_pose3d_estimation_pipeline import WiLorHandPose3dEstimationPipeline
        self.device = torch.device(device)
        kwargs = {"device": self.device, "verbose": False}
        if pretrained_dir:
            kwargs["wilor_pretrained_dir"] = pretrained_dir
        self.pipeline = WiLorHandPose3dEstimationPipeline(**kwargs)
        self.size = self.pipeline.IMAGE_SIZE

    def _move_to_cpu(self) -> None:
        self.pipeline.wilor_model.to("cpu")
        hand_detector = getattr(self.pipeline, "hand_detector", None)
        if hand_detector is not None:
            try:
                hand_detector.to("cpu")
            except Exception:
                # Direct batched WiLoR inference does not use this detector.
                pass
        self.pipeline.device = torch.device("cpu")
        self.device = torch.device("cpu")

    def _forward(self, patches: list[np.ndarray]):
        stacked = np.stack(patches)
        def infer(active_device):
            batch = torch.from_numpy(stacked).to(
                device=active_device, dtype=self.pipeline.dtype
            )
            with torch.no_grad():
                return self.pipeline.wilor_model(batch)
        output,actual_device = run_with_device_fallback(
            infer,
            self.device,
            label="WiLoR hand-pose inference",
            on_cpu_fallback=self._move_to_cpu,
        )
        self.device = torch.device(actual_device)
        return output

    def infer(self, frames: list[np.ndarray], roi: np.ndarray, right: bool) -> np.ndarray:
        return self.infer_rois(frames, [roi] * len(frames), right)

    def infer_rois(self, frames: list[np.ndarray], rois: list[np.ndarray], right: bool) -> np.ndarray:
        """Infer a batch in which each frame may have a different crop."""
        from app.analysis.models.wilor_mini.utils import utils
        if len(frames) != len(rois):
            raise ValueError("frames and rois must have the same length")
        patches = []
        for image, roi in zip(frames, rois):
            cx, cy = (roi[:2] + roi[2:]) / 2
            side = float(max(roi[2] - roi[0], roi[3] - roi[1]))
            source = image
            factor = side / self.size / 2
            if factor > 1.1:
                source = gaussian(source, sigma=(factor - 1) / 2, channel_axis=2, preserve_range=True)
            patch, _ = utils.generate_image_patch_cv2(source, cx, cy, side, side, self.size, self.size,
                                                       do_flip=not right, scale=1.0, rot=0,
                                                       border_mode=cv2.BORDER_CONSTANT)
            patches.append(patch)
        keypoints = self._forward(patches)["pred_keypoints_3d"].cpu().float().numpy()
        if not right:
            keypoints[:, :, 0] *= -1
        return keypoints

    def infer_rois_with_projection(self, frames: list[np.ndarray], rois: list[np.ndarray],
                                   right: bool) -> tuple[np.ndarray, np.ndarray]:
        """Batch inference returning 3-D landmarks and full-frame 2-D projections.

        This is mathematically equivalent to WiLoR ``predict_with_bboxes`` but
        keeps the validated batch path. Each frame has its own YOLO hand ROI.
        """
        from app.analysis.models.wilor_mini.utils import utils
        if len(frames) != len(rois):
            raise ValueError("frames and rois must have the same length")
        patches, centers, sides, image_sizes = [], [], [], []
        for image, roi in zip(frames, rois):
            center = (roi[:2] + roi[2:]) / 2
            side = float(max(roi[2] - roi[0], roi[3] - roi[1]))
            source = image
            factor = side / self.size / 2
            if factor > 1.1:
                source = gaussian(source, sigma=(factor - 1) / 2, channel_axis=2, preserve_range=True)
            patch, _ = utils.generate_image_patch_cv2(
                source, center[0], center[1], side, side, self.size, self.size,
                do_flip=not right, scale=1.0, rot=0, border_mode=cv2.BORDER_CONSTANT)
            patches.append(patch); centers.append(center); sides.append(side)
            image_sizes.append(np.array([image.shape[1], image.shape[0]], float))
        output = self._forward(patches)
        keypoints = output["pred_keypoints_3d"].cpu().float().numpy()
        cameras = output["pred_cam"].cpu().float().numpy()
        projections = []
        for index, (center, side, image_size) in enumerate(zip(centers, sides, image_sizes)):
            camera = cameras[[index]].copy()
            camera[:, 1] *= 1 if right else -1
            points = keypoints[[index]].copy()
            if not right:
                points[:, :, 0] *= -1
            focal = self.pipeline.FOCAL_LENGTH / self.pipeline.IMAGE_SIZE * image_size.max()
            translation = utils.cam_crop_to_full(camera, center[None], side,
                                                 image_size[None], focal)
            projected = utils.perspective_projection(
                points, translation=translation,
                focal_length=np.array([focal, focal])[None],
                camera_center=image_size[None] / 2)
            projections.append(projected[0])
            keypoints[index] = points[0]
        return keypoints, np.stack(projections)


def geometry_angle(keypoints: np.ndarray, resolve_normals: bool = True) -> np.ndarray:
    """Roll around wrist-to-middle-MCP axis, referenced to projected camera vertical."""
    wrist, index, middle, little = (keypoints[:, i] for i in (0, 5, 9, 17))
    axis = middle - wrist; axis /= np.linalg.norm(axis, axis=1, keepdims=True).clip(1e-8)
    across = index - little
    across -= (across * axis).sum(1, keepdims=True) * axis
    across /= np.linalg.norm(across, axis=1, keepdims=True).clip(1e-8)
    # WiLoR can occasionally reverse the palm normal in an ambiguous edge-on
    # frame. At video frame rates a real hand cannot rotate 180° instantly, so
    # choose the normal branch continuous with the preceding frame.
    normals = np.cross(axis, across)
    normals /= np.linalg.norm(normals, axis=1, keepdims=True).clip(1e-8)
    if resolve_normals:
        for i in range(1, len(across)):
            if np.dot(normals[i], normals[i - 1]) < 0:
                across[i] *= -1
                normals[i] *= -1
    vertical = np.tile(np.array([0., 1., 0.]), (len(axis), 1))
    vertical -= (vertical * axis).sum(1, keepdims=True) * axis
    vertical /= np.linalg.norm(vertical, axis=1, keepdims=True).clip(1e-8)
    orthogonal = np.cross(axis, vertical)
    return np.degrees(np.arctan2((across * orthogonal).sum(1), (across * vertical).sum(1)))


def palm_normal_angle(keypoints: np.ndarray, right: bool) -> np.ndarray:
    """Notebook-compatible palm-normal angle with deterministic sign continuity."""
    points = np.asarray(keypoints, float)
    forward = points[:, 1] - points[:, 0]
    forward /= np.linalg.norm(forward, axis=1, keepdims=True).clip(1e-8)
    side = points[:, 7] - points[:, 0]
    side -= np.sum(side * forward, axis=1, keepdims=True) * forward
    side /= np.linalg.norm(side, axis=1, keepdims=True).clip(1e-8)
    normals = np.cross(forward, side)
    normals /= np.linalg.norm(normals, axis=1, keepdims=True).clip(1e-8)
    for frame in range(len(normals)):
        palm_should_face = ((points[frame, 4, 0] < points[frame, 20, 0]) if right else
                            (points[frame, 4, 0] > points[frame, 20, 0]))
        if palm_should_face != (normals[frame, 2] < 0):
            normals[frame] *= -1
        if frame and np.dot(normals[frame], normals[frame - 1]) < 0:
            normals[frame] *= -1
    angle = np.degrees(np.arctan2(normals[:, 1], normals[:, 0]))
    return angle if right else -angle


def choose_angle_estimator(current: np.ndarray, palm_normal: np.ndarray,
                           raw_reference: np.ndarray) -> tuple[np.ndarray, str, float, float]:
    """Choose palm-normal only when it has a material plausibility advantage."""
    def score(values: np.ndarray, reference_range: float) -> float:
        velocity = np.abs(np.diff(values))
        acceleration = np.abs(np.diff(values, n=2))
        robust_range = float(np.percentile(values, 95) - np.percentile(values, 5))
        allowed = max(1.75 * reference_range, reference_range + 180.0)
        return ((float(np.max(velocity)) if len(velocity) else 0.0) +
                (0.25 * float(np.percentile(acceleration, 95)) if len(acceleration) else 0.0) +
                2.0 * max(0.0, robust_range - allowed))
    reference_range = float(np.percentile(raw_reference, 95) - np.percentile(raw_reference, 5))
    current_score = score(current, reference_range)
    palm_score = score(palm_normal, reference_range)
    current_range = float(np.percentile(current, 95) - np.percentile(current, 5))
    palm_range = float(np.percentile(palm_normal, 95) - np.percentile(palm_normal, 5))
    # A smoother candidate is not an improvement if it doubles the inferred
    # ROM; that is the palm-normal winding failure seen in the 615-frame 006 copy.
    range_compatible = palm_range <= max(1.5 * current_range, current_range + 90.0)
    if range_compatible and palm_score + 5.0 < current_score:
        return palm_normal, "palm_normal", current_score, palm_score
    return current, "geometry", current_score, palm_score


def zero_phase_lowpass(values: np.ndarray, fps: float, cutoff_hz: float = 10.0,
                       order: int = 4) -> tuple[np.ndarray, float]:
    """Low-pass a trajectory with forward/backward filtering (zero phase lag)."""
    values = np.asarray(values, dtype=float)
    effective_cutoff = min(float(cutoff_hz), 0.45 * float(fps))
    if len(values) < 16 or effective_cutoff <= 0:
        return values.copy(), effective_cutoff
    sos = butter(order, effective_cutoff, btype="lowpass", fs=fps, output="sos")
    return sosfiltfilt(sos, values), effective_cutoff


def angle_anomaly_diagnostics(angles: np.ndarray, landmark_quality: np.ndarray,
                              fps: float) -> tuple[np.ndarray, np.ndarray]:
    """Detect corrupt multi-frame intervals without changing their samples."""
    angles = np.asarray(angles, float)
    quality = np.asarray(landmark_quality, float)
    velocity = np.r_[0.0, np.abs(np.diff(angles))]
    acceleration = np.r_[0.0, 0.0, np.abs(np.diff(angles, n=2))]
    window = max(3, int(round(0.12 * fps)))
    series = pd.Series(angles)
    window_range = (series.rolling(window, center=True, min_periods=2).max() -
                    series.rolling(window, center=True, min_periods=2).min()).to_numpy()
    local_quality = pd.Series(quality).rolling(window, center=True, min_periods=1).min().to_numpy()
    score = np.maximum.reduce((velocity / 60.0, acceleration / 75.0,
                               window_range / 120.0, (1.0 - quality) / 0.85))
    low_confidence = ((quality < 0.15) |
                      ((window_range > 90.0) & (local_quality < 0.25)) |
                      (acceleration > 75.0))
    return score.astype(np.float32), low_confidence


def repair_uncertain_angle_samples(angles: np.ndarray, low_confidence: np.ndarray,
                                   fps: float, residual_deg: float = 40.0) -> tuple[np.ndarray, np.ndarray]:
    """Replace only independently unreliable local outliers with a robust median.

    The observation is retained unless both the landmark/temporal diagnostics
    mark it unreliable and it disagrees strongly with a centred 0.35 s median.
    This avoids the earlier failure where a jump threshold damaged good data.
    """
    values = np.asarray(angles, float)
    window = max(5, int(round(0.35 * fps)))
    if window % 2 == 0:
        window += 1
    local = pd.Series(values).rolling(window, center=True, min_periods=max(3, window // 3)).median().to_numpy()
    replace = np.asarray(low_confidence, bool) & np.isfinite(local) & (np.abs(values - local) > residual_deg)
    repaired = values.copy()
    repaired[replace] = local[replace]
    return repaired, replace


def landmark_temporal_decode(keypoints: np.ndarray, switch_penalty: float = 0.08,
                             branch_jump_gate_deg: float = 100.0) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Select a temporally continuous palm-orientation branch using all 21 landmarks.

    State 0 retains WiLoR's landmarks. State 1 rotates the hand 180 degrees
    around its wrist-to-middle-MCP axis. This rigid alternative preserves bone
    lengths and finger articulation. A two-state Viterbi pass selects the
    lowest-cost path over the complete video; no landmarks are interpolated.
    """
    raw = np.asarray(keypoints, dtype=np.float32)
    if raw.ndim != 3 or raw.shape[1:] != (21, 3):
        raise ValueError(f"Expected landmarks shaped (frames, 21, 3), got {raw.shape}")
    n = len(raw)
    if n == 0:
        return raw.copy(), {"branch_flipped": np.zeros(0, bool)}

    wrist = raw[:, 0]
    axis = raw[:, 9] - wrist
    axis /= np.linalg.norm(axis, axis=1, keepdims=True).clip(1e-8)
    relative = raw - wrist[:, None, :]
    rotated = wrist[:, None, :] + (
        2.0 * np.sum(relative * axis[:, None, :], axis=2, keepdims=True) * axis[:, None, :] - relative
    )
    candidates = np.stack((raw, rotated), axis=1)  # frames, state, landmarks, xyz

    # Wrist-centred, scale-normalised shape makes the continuity cost invariant
    # to crop scale and global camera translation.
    centered = candidates - candidates[:, :, :1, :]
    palm_scale = np.linalg.norm(raw[:, 9] - raw[:, 0], axis=1).clip(1e-8)
    normalized = centered / palm_scale[:, None, None, None]
    normals = np.cross(normalized[:, :, 9], normalized[:, :, 5] - normalized[:, :, 17])
    normals /= np.linalg.norm(normals, axis=2, keepdims=True).clip(1e-8)
    raw_angles = geometry_angle(raw, resolve_normals=False)
    circular_angle_steps = np.abs((np.diff(raw_angles) + 180.0) % 360.0 - 180.0)

    cost = np.full((n, 2), np.inf, dtype=np.float64)
    parent = np.zeros((n, 2), dtype=np.int8)
    # Anchor the first frame to WiLoR's branch. There is deliberately no
    # per-frame penalty for remaining flipped: a long erroneous interval must
    # not eventually overpower continuity merely because it is long.
    cost[0] = (0.0, switch_penalty)
    for frame in range(1, n):
        for state in (0, 1):
            options = []
            for previous in (0, 1):
                # A state transition changes the inferred angle by 180 degrees.
                # Permit it only where WiLoR itself made a very large circular
                # angular jump. This prevents legitimate, smooth P/S motion
                # from being reinterpreted merely to reduce landmark RMS.
                if state != previous and circular_angle_steps[frame - 1] < branch_jump_gate_deg:
                    options.append(np.inf)
                    continue
                rms = float(np.sqrt(np.mean((normalized[frame, state] - normalized[frame - 1, previous]) ** 2)))
                normal_cost = float(0.04 * (1.0 - np.dot(normals[frame, state], normals[frame - 1, previous])))
                transition = switch_penalty if state != previous else 0.0
                options.append(cost[frame - 1, previous] + rms + normal_cost + transition)
            parent[frame, state] = int(np.argmin(options))
            cost[frame, state] = options[parent[frame, state]]
    states = np.zeros(n, dtype=np.int8)
    states[-1] = int(np.argmin(cost[-1]))
    for frame in range(n - 1, 0, -1):
        states[frame - 1] = parent[frame, states[frame]]
    viterbi_corrected = candidates[np.arange(n), states]

    # Conservative fallback: a nearest-palm-normal path is less ambitious but
    # cannot be lured into changing branches by unrelated finger articulation.
    greedy_states = np.zeros(n, dtype=np.int8)
    selected_normal = normals[0, 0]
    for frame in range(1, n):
        greedy_states[frame] = int(np.dot(normals[frame, 1], selected_normal) >
                                   np.dot(normals[frame, 0], selected_normal))
        selected_normal = normals[frame, greedy_states[frame]]
    greedy_corrected = candidates[np.arange(n), greedy_states]

    candidate_angles = np.stack((geometry_angle(candidates[:, 0], resolve_normals=False),
                                 geometry_angle(candidates[:, 1], resolve_normals=False)), axis=1)

    def validated_intervals(proposed: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Keep only bounded branch intervals that improve both boundaries."""
        proposed = proposed.astype(np.int8).copy()
        # A global 180-degree rotation is equivalent after initial calibration;
        # use that freedom to anchor every hypothesis to state zero.
        if proposed[0]:
            proposed = 1 - proposed
        rejected = np.zeros(n, dtype=bool)
        index = 0
        while index < n:
            if proposed[index] == 0:
                index += 1
                continue
            start = index
            while index < n and proposed[index] == 1:
                index += 1
            end = index
            valid = end < n  # a one-sided persistent offset has no exit evidence
            if valid:
                def circular_step(current: float, previous: float) -> float:
                    return abs((current - previous + 180.0) % 360.0 - 180.0)
                raw_entry = circular_step(candidate_angles[start, 0], candidate_angles[start - 1, 0])
                fixed_entry = circular_step(candidate_angles[start, 1], candidate_angles[start - 1, 0])
                raw_exit = circular_step(candidate_angles[end, 0], candidate_angles[end - 1, 0])
                fixed_exit = circular_step(candidate_angles[end, 0], candidate_angles[end - 1, 1])
                valid = (fixed_entry < 60.0 and fixed_exit < 60.0 and
                         fixed_entry < 0.7 * raw_entry and fixed_exit < 0.7 * raw_exit)
            if not valid:
                proposed[start:end] = 0
                rejected[start:end] = True
        return proposed, rejected

    states, viterbi_rejected = validated_intervals(states)
    greedy_states, greedy_rejected = validated_intervals(greedy_states)
    viterbi_corrected = candidates[np.arange(n), states]
    greedy_corrected = candidates[np.arange(n), greedy_states]

    def angle_plausibility(points: np.ndarray) -> tuple[float, float]:
        angle = np.degrees(np.unwrap(np.radians(geometry_angle(points, resolve_normals=False))))
        max_step = float(np.max(np.abs(np.diff(angle)))) if len(angle) > 1 else 0.0
        robust_range = float(np.percentile(angle, 95) - np.percentile(angle, 5))
        return max_step, robust_range

    def trajectory_score(points: np.ndarray, raw_range: float) -> tuple[float, dict[str, float]]:
        """Score a branch path without imposing an absolute ROM limit."""
        angle = np.degrees(np.unwrap(np.radians(geometry_angle(points, resolve_normals=False))))
        velocity = np.abs(np.diff(angle))
        acceleration = np.abs(np.diff(angle, n=2))
        robust_range = float(np.percentile(angle, 95) - np.percentile(angle, 5))
        velocity_p95 = float(np.percentile(velocity, 95)) if len(velocity) else 0.0
        velocity_max = float(np.max(velocity)) if len(velocity) else 0.0
        acceleration_p95 = float(np.percentile(acceleration, 95)) if len(acceleration) else 0.0
        # This is relative to the video's own raw trajectory, not a fixed
        # physiological boundary. It therefore permits genuine large smooth
        # motion, including a moving shoulder/body baseline.
        allowed_range = max(1.75 * raw_range, raw_range + 180.0)
        range_expansion = max(0.0, robust_range - allowed_range)
        # A p95-only statistic hid a single destructive branch boundary in
        # PPB_CON023. The maximum step is therefore explicit; this selects the
        # untouched path when a proposed correction merely moves the jump.
        score = velocity_max + 0.25 * acceleration_p95 + 2.0 * range_expansion
        return score, {"score": score, "range": robust_range,
                       "range_expansion": range_expansion}

    _, raw_range = angle_plausibility(raw)
    paths = {
        "raw_identity": (raw, np.zeros(n, dtype=np.int8)),
        "gated_viterbi": (viterbi_corrected, states.copy()),
        "conservative_palm_normal": (greedy_corrected, greedy_states),
    }
    scored = {name: trajectory_score(points, raw_range) for name, (points, _) in paths.items()}
    # Prefer the observation unless a corrected hypothesis wins by a useful
    # margin. Every state boundary is another inferred (not observed) event.
    for name, (_, path_states) in paths.items():
        if name == "raw_identity":
            continue
        complexity = 5.0 + 2.0 * float(np.sum(np.diff(path_states) != 0))
        base_score, details = scored[name]
        details["complexity_penalty"] = complexity
        details["score"] = base_score + complexity
        scored[name] = (base_score + complexity, details)
    decoder_mode = min(scored, key=lambda name: scored[name][0])
    corrected, states = paths[decoder_mode]
    rejected_intervals = ({"raw_identity": np.zeros(n, bool),
                           "gated_viterbi": viterbi_rejected,
                           "conservative_palm_normal": greedy_rejected}[decoder_mode])

    def normalized_steps(points: np.ndarray) -> np.ndarray:
        p = points - points[:, :1]
        p = p / palm_scale[:, None, None]
        return np.r_[0.0, np.sqrt(np.mean(np.diff(p, axis=0) ** 2, axis=(1, 2)))]

    raw_steps = normalized_steps(raw)
    corrected_steps = normalized_steps(corrected)
    # Bone-length variation is an anatomical reliability signal. The branch
    # transform is rigid, so this reports the original WiLoR fit quality.
    edges = np.asarray([(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
                        (0, 9), (9, 10), (10, 11), (11, 12), (0, 13), (13, 14), (14, 15),
                        (15, 16), (0, 17), (17, 18), (18, 19), (19, 20)])
    lengths = np.linalg.norm(raw[:, edges[:, 1]] - raw[:, edges[:, 0]], axis=2)
    reference_lengths = np.median(lengths, axis=0).clip(1e-8)
    bone_error = np.median(np.abs(lengths / reference_lengths - 1.0), axis=1)
    quality = np.exp(-corrected_steps / 0.12) * np.exp(-bone_error / 0.12)
    quality[states.astype(bool)] *= 0.8
    diagnostics = {
        "branch_flipped": states.astype(bool),
        "landmark_step_raw": raw_steps,
        "landmark_step_corrected": corrected_steps,
        "bone_length_relative_error": bone_error,
        "landmark_quality_score": np.clip(quality, 0.0, 1.0),
        "decoder_mode": np.asarray(decoder_mode),
        "trajectory_score": np.full(n, scored[decoder_mode][1]["score"], dtype=np.float32),
        "trajectory_range_deg": np.full(n, scored[decoder_mode][1]["range"], dtype=np.float32),
        "trajectory_range_expansion_deg": np.full(
            n, scored[decoder_mode][1]["range_expansion"], dtype=np.float32),
        "branch_changed": np.r_[False, np.diff(states) != 0],
        "branch_interval_rejected": rejected_intervals,
    }
    return corrected.astype(np.float32), diagnostics


def repair_short_flip_intervals(angles: np.ndarray, max_step_deg: float = 120,
                                max_interval_frames: int = 35) -> tuple[np.ndarray, np.ndarray]:
    """Correct only strongly supported, bounded 180/360-degree branch offsets.

    A valid repair must have two large boundary jumps and one constant branch
    offset must substantially improve continuity at *both* boundaries.  The
    interval is shifted intact; its observed motion is never replaced by a
    straight line.  Ambiguous jumps are left unchanged for quality flagging.
    """
    repaired = np.asarray(angles, dtype=float).copy()
    repaired_flag = np.zeros(len(repaired), dtype=bool)
    steps = np.diff(repaired)
    edges = np.flatnonzero(np.abs(steps) >= max_step_deg)
    used_through = -1
    for position, start in enumerate(edges):
        if start <= used_through:
            continue
        best = None
        for end in edges[position + 1:]:
            if end - start > max_interval_frames:
                break
            if end <= start or steps[start] * steps[end] >= 0:
                continue
            for shift in (-360.0, -180.0, 180.0, 360.0):
                before = abs(steps[start]) + abs(steps[end])
                after_entry = abs(steps[start] + shift)
                after_exit = abs(steps[end] - shift)
                after = after_entry + after_exit
                # Both corrected boundaries must become physiologically modest,
                # and total discontinuity must fall by at least 65%.
                if after_entry <= max_step_deg / 2 and after_exit <= max_step_deg / 2 and after <= .35 * before:
                    candidate = (after, int(end), shift)
                    if best is None or candidate < best:
                        best = candidate
        if best is None:
            continue
        _, end, shift = best
        repaired[start + 1:end + 1] += shift
        repaired_flag[start + 1:end + 1] = True
        used_through = end
    return repaired, repaired_flag


def temporal_branch_decode(angles: np.ndarray, jump_threshold_deg: float = 65,
                           persistence_frames: int = 5) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Correct persistent ±180/±360 degree branch shifts conservatively.

    WiLoR is frame-independent.  After short intervals have been repaired,
    a remaining near-instantaneous 180/360-degree change that persists for
    several frames is almost certainly a pose-interpretation branch change,
    rather than physiological P/S motion.  The returned quality score is a
    temporal consistency proxy, not a calibrated model probability.
    """
    raw = np.asarray(angles, dtype=float)
    corrected = raw.copy()
    offsets = np.zeros(len(raw), dtype=float)
    branch_fixed = np.zeros(len(raw), dtype=bool)
    if len(raw) < 2:
        return corrected, offsets, branch_fixed, np.ones(len(raw), dtype=float)
    offset = 0.0
    for i in range(1, len(raw)):
        current = raw[i] + offset
        step = current - corrected[i - 1]
        if abs(step) > jump_threshold_deg:
            # Try the branch offsets that appear in the observed failure mode.
            candidates = []
            for shift in (-360.0, -180.0, 0.0, 180.0, 360.0):
                new_step = current + shift - corrected[i - 1]
                candidates.append((abs(new_step) + (10.0 if shift else 0.0), shift, new_step))
            _, shift, new_step = min(candidates)
            # A branch correction must make the discontinuity clearly smaller
            # and remain plausible for several following raw observations.
            if shift and abs(new_step) < jump_threshold_deg and abs(new_step) < .55 * abs(step):
                end = min(len(raw), i + persistence_frames)
                local_steps = np.abs(np.diff(raw[i:end]))
                if len(local_steps) == 0 or np.nanmedian(local_steps) < jump_threshold_deg:
                    offset += shift
                    current += shift
                    branch_fixed[i:end] = True
        corrected[i] = current
        offsets[i] = offset
    # A local median residual exposes isolated noisy frames that did not merit
    # an angle correction.  It is used only as a quality indicator.
    series = pd.Series(corrected)
    local_median = series.rolling(5, center=True, min_periods=1).median().to_numpy()
    residual = np.abs(corrected - local_median)
    steps = np.r_[0.0, np.abs(np.diff(corrected))]
    quality = np.exp(-residual / 35.0) * np.exp(-steps / 70.0)
    quality[branch_fixed] *= .75
    return corrected, offsets, branch_fixed, np.clip(quality, 0.0, 1.0)


def save_angle_plot(table: pd.DataFrame, output_path: Path, source_column: str, initial: float) -> None:
    """Write a compact, self-contained angle plot alongside angles.csv."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 4.5), constrained_layout=True)
    raw = table["angle_geometry_unwrapped_deg"] - initial
    if source_column != "angle_geometry_unwrapped_deg":
        ax.plot(table["time_s"], raw, color="0.70", linewidth=1, label="Raw (unwrapped)")
    ax.plot(table["time_s"], table["angle_palm_down_relative_deg"], color="#1976d2", linewidth=1.5,
            label="Final angle")
    if "flip_interval_repaired" in table and table["flip_interval_repaired"].any():
        repaired = table["flip_interval_repaired"]
        ax.scatter(table.loc[repaired, "time_s"], table.loc[repaired, "angle_palm_down_relative_deg"],
                   s=8, color="#d32f2f", label="Short flip repaired", zorder=3)
    ax.axhline(0, color="0.2", linewidth=.8)
    ax.set(xlabel="Time (s)", ylabel="Angle (degrees)", title="WiLoR hand angle")
    ax.grid(alpha=.25)
    ax.legend(loc="best")
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def run_video(video: str, detector, detector_name: str, hand: str, device: str, batch_size: int,
              localization_fps: float, crop_scale: float, output_dir: str | None = None,
              roi_seconds: float = 0, repair_flips: bool = False,
              wilor_pretrained_dir: str | None = None,
              wilor_model: WiLorBatch | None = None,
              landmark_temporal: bool = False,
              save_landmarks: bool = False) -> Path:
    cap = cv2.VideoCapture(video)
    if not cap.isOpened(): raise FileNotFoundError(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    step = max(1, round(fps / localization_fps)); samples: dict[int, list[np.ndarray]] = {}
    frame_id = 0
    while True:
        ok, frame = cap.read()
        if not ok: break
        if frame_id % step == 0:
            boxes = detector(frame)
            if boxes: samples[frame_id] = boxes
        frame_id += 1
    cap.release()
    timed_track = select_moving_track_timed(samples)
    track = [box for _, box in timed_track]
    roi = square_roi(track, width, height, crop_scale)
    right = hand == "right" or (hand == "auto" and np.mean([(b[0]+b[2])/2 for b in track]) > width/2)
    segment_frames = max(1, round(roi_seconds * fps)) if roi_seconds else n_frames
    segment_rois = {}
    for segment in range((n_frames + segment_frames - 1) // segment_frames):
        start, end = segment * segment_frames, (segment + 1) * segment_frames
        boxes = [box for frame, box in timed_track if start <= frame < end]
        segment_rois[segment] = square_roi(boxes, width, height, crop_scale) if len(boxes) >= 2 else roi
    out = Path(output_dir or f"results/{Path(video).stem}_{detector_name}"); out.mkdir(parents=True, exist_ok=True)
    preview = np.zeros((height, width, 3), dtype=np.uint8)
    preview[:] = (20, 20, 20)
    for b in track: cv2.rectangle(preview, tuple(b[:2].astype(int)), tuple(b[2:].astype(int)), (0, 170, 255), 1)
    for segment, segment_roi in segment_rois.items():
        color = (0, 255, 0) if segment == 0 else (255, 180, 0)
        cv2.rectangle(preview, tuple(segment_roi[:2].astype(int)), tuple(segment_roi[2:].astype(int)), color, 2)
    cv2.imwrite(str(out / "localization_preview.jpg"), preview)
    # A batch caller supplies one shared WiLorBatch instance, avoiding the
    # expensive model initialization once per video.
    model = wilor_model or WiLorBatch(device, wilor_pretrained_dir); cap = cv2.VideoCapture(video); pending = []; ids = []; current_roi = None
    all_ids: list[int] = []
    landmark_chunks: list[np.ndarray] = []
    def flush():
        if not pending: return
        kp = model.infer(pending, current_roi, right)
        landmark_chunks.append(kp)
        all_ids.extend(ids)
        pending.clear(); ids.clear()
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok: break
        next_roi = segment_rois[i // segment_frames]
        if current_roi is not None and not np.array_equal(next_roi, current_roi): flush()
        current_roi = next_roi
        pending.append(frame); ids.append(i)
        if len(pending) >= batch_size: flush()
        i += 1
    flush(); cap.release()
    raw_landmarks = np.concatenate(landmark_chunks, axis=0)
    if landmark_temporal:
        corrected_landmarks, landmark_diagnostics = landmark_temporal_decode(raw_landmarks)
    else:
        corrected_landmarks = raw_landmarks.copy()
        landmark_diagnostics = {
            "branch_flipped": np.zeros(len(raw_landmarks), dtype=bool),
            "landmark_step_raw": np.r_[0.0, np.full(max(0, len(raw_landmarks) - 1), np.nan)],
            "landmark_step_corrected": np.r_[0.0, np.full(max(0, len(raw_landmarks) - 1), np.nan)],
            "bone_length_relative_error": np.full(len(raw_landmarks), np.nan),
            "landmark_quality_score": np.ones(len(raw_landmarks)),
        }
    raw_angles = geometry_angle(raw_landmarks, resolve_normals=False)
    selected_angles = geometry_angle(corrected_landmarks, resolve_normals=False)
    table = pd.DataFrame({"frame_idx": all_ids, "time_s": np.asarray(all_ids) / fps,
                          "angle_geometry_raw_deg": raw_angles,
                          "landmark_branch_flipped": landmark_diagnostics["branch_flipped"],
                          "landmark_step_raw": landmark_diagnostics["landmark_step_raw"],
                          "landmark_step_corrected": landmark_diagnostics["landmark_step_corrected"],
                          "bone_length_relative_error": landmark_diagnostics["bone_length_relative_error"],
                          "landmark_quality_score": landmark_diagnostics["landmark_quality_score"]})
    table["angle_landmark_selected_raw_deg"] = selected_angles
    table["angle_geometry_unwrapped_deg"] = np.degrees(np.unwrap(np.radians(table.angle_geometry_raw_deg)))
    table["angle_landmark_selected_unwrapped_deg"] = np.degrees(np.unwrap(np.radians(selected_angles)))
    if landmark_temporal:
        wrist = raw_landmarks[:, 0]
        axis = raw_landmarks[:, 9] - wrist
        axis /= np.linalg.norm(axis, axis=1, keepdims=True).clip(1e-8)
        relative = raw_landmarks - wrist[:, None, :]
        alternative_landmarks = wrist[:, None, :] + (
            2.0 * np.sum(relative * axis[:, None, :], axis=2, keepdims=True) * axis[:, None, :] - relative)
        alternative = geometry_angle(alternative_landmarks, resolve_normals=False)
        table["angle_original_branch_deg"] = table["angle_geometry_unwrapped_deg"]
        table["angle_alternative_branch_deg"] = np.degrees(np.unwrap(np.radians(alternative)))
        table["angle_selected_corrected_deg"] = table["angle_landmark_selected_unwrapped_deg"]
        table["selected_branch"] = landmark_diagnostics["branch_flipped"].astype(np.int8)
        table["branch_changed"] = landmark_diagnostics["branch_changed"]
        table["branch_interval_rejected"] = landmark_diagnostics["branch_interval_rejected"]
        table["trajectory_score"] = landmark_diagnostics["trajectory_score"]
        table["trajectory_range_expansion_deg"] = landmark_diagnostics["trajectory_range_expansion_deg"]
    source_column = "angle_landmark_selected_unwrapped_deg" if landmark_temporal else "angle_geometry_unwrapped_deg"
    palm_candidate = np.degrees(np.unwrap(np.radians(palm_normal_angle(raw_landmarks, right))))
    table["angle_palm_normal_candidate_deg"] = palm_candidate
    chosen, angle_method, geometry_score, palm_score = choose_angle_estimator(
        table[source_column].to_numpy(), palm_candidate,
        table["angle_geometry_unwrapped_deg"].to_numpy())
    table["angle_estimator_selected_deg"] = chosen
    table["angle_estimator_method"] = angle_method
    table["angle_geometry_method_score"] = geometry_score
    table["angle_palm_normal_method_score"] = palm_score
    source_column = "angle_estimator_selected_deg"
    if repair_flips:
        repaired, flags = repair_short_flip_intervals(table[source_column].to_numpy(), max_interval_frames=round(fps * .6))
        table["angle_geometry_repaired_deg"] = repaired
        table["flip_interval_repaired"] = flags
        source_column = "angle_geometry_repaired_deg"
    table["angle_temporal_unfiltered_deg"] = table[source_column]
    anomaly_score, low_confidence = angle_anomaly_diagnostics(
        table[source_column].to_numpy(), table["landmark_quality_score"].to_numpy(), fps)
    table["angle_anomaly_score"] = anomaly_score
    table["angle_low_confidence"] = low_confidence
    replacement_evidence = low_confidence & (table["landmark_quality_score"].to_numpy() < 0.05)
    repaired_uncertain, uncertain_replaced = repair_uncertain_angle_samples(
        table[source_column].to_numpy(), replacement_evidence, fps)
    table["angle_uncertain_repaired_deg"] = repaired_uncertain
    table["uncertain_sample_replaced"] = uncertain_replaced
    filtered, effective_cutoff = zero_phase_lowpass(repaired_uncertain, fps, 10.0)
    table["angle_final_lowpass_deg"] = filtered
    source_column = "angle_final_lowpass_deg"
    initial = table.loc[table.time_s <= min(0.5, table.time_s.max()), source_column].median()
    table["angle_palm_down_relative_deg"] = table[source_column] - initial
    table.to_csv(out / "angles.csv", index=False)
    if save_landmarks or landmark_temporal:
        np.savez_compressed(out / "landmarks.npz", frame_idx=np.asarray(all_ids, dtype=np.int32),
                            raw=raw_landmarks, corrected=corrected_landmarks,
                            **landmark_diagnostics)
    save_angle_plot(table, out / "angles.png", source_column, initial)
    video_path = Path(video).resolve()
    (out / "summary.json").write_text(json.dumps({"video": video, "detector": detector_name, "fps": fps,
        "frames": n_frames, "roi_xyxy": roi.tolist(), "roi_seconds": roi_seconds, "repair_short_flips": repair_flips,
        "source_video": {"path": str(video_path), "size_bytes": video_path.stat().st_size,
                         "sha256": file_sha256(video_path), "frames": n_frames, "fps": fps,
                         "duration_s": n_frames / fps, "width": width, "height": height},
        "segment_rois_xyxy": {str(k): v.tolist() for k, v in segment_rois.items()}, "hand": hand,
        "resolved_right": right, "localization_samples": len(samples),
        "landmark_temporal": landmark_temporal, "landmarks_saved": bool(save_landmarks or landmark_temporal),
        "landmark_branch_frames": int(np.sum(landmark_diagnostics["branch_flipped"])),
        "landmark_decoder_mode": (str(landmark_diagnostics.get("decoder_mode"))
                                  if landmark_temporal else "disabled"),
        "lowpass": {"type": "Butterworth SOS forward-backward", "order": 4,
                    "requested_cutoff_hz": 10.0, "effective_cutoff_hz": effective_cutoff,
                    "zero_phase": True},
        "low_confidence_fraction": float(np.mean(low_confidence)),
        "uncertain_samples_replaced": int(np.sum(uncertain_replaced)),
        "angle_estimator_method": angle_method,
        "angle_estimator_scores": {"geometry": geometry_score, "palm_normal": palm_score},
        "wilor_pretrained_dir": wilor_pretrained_dir}, indent=2))
    return out
