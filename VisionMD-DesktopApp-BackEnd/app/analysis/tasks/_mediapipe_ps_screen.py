"""Fast, provisional MediaPipe 3-D screening for pronation/supination.

MediaPipe world landmarks are monocular estimates and are not treated as a
drop-in replacement for WiLoR. This module accepts only technically clean
tracks; accepted results remain explicitly marked as requiring verification.
"""
from __future__ import annotations

import cv2
import mediapipe as mp
import numpy as np

from app.analysis.detectors.mp_hand_detector import HandDetector


def _interpolate_track(values: np.ndarray) -> np.ndarray:
    output = values.copy()
    frames = np.arange(len(output))
    for landmark in range(output.shape[1]):
        for coordinate in range(output.shape[2]):
            series = output[:, landmark, coordinate]
            valid = np.isfinite(series)
            if valid.sum() < 2:
                raise ValueError("Too few MediaPipe 3-D observations")
            output[:, landmark, coordinate] = np.interp(frames, frames[valid], series[valid])
    return output


def screen_mediapipe_world_landmarks(video_path, rotation, start_frame, end_frame,
                                     fps, subject_box, requested_right,
                                     process_landmarks):
    """Return a provisional track dict, or a rejected diagnostic dict."""
    x1 = max(0, int(subject_box["x"])); y1 = max(0, int(subject_box["y"]))
    x2 = x1 + max(1, int(subject_box["width"])); y2 = y1 + max(1, int(subject_box["height"]))
    expected = max(0, end_frame - start_frame)
    raw = np.full((expected, 21, 3), np.nan, dtype=np.float32)
    projected = np.full((expected, 21, 2), np.nan, dtype=np.float32)
    detector = HandDetector().get_detector()
    cap = cv2.VideoCapture(video_path); cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    detected = 0
    try:
        for local_index in range(expected):
            ok, frame = cap.read()
            if not ok: break
            from app.analysis.tasks.base_task import BaseTask
            frame = BaseTask.correct_frame_orientation(frame, rotation)
            height, width = frame.shape[:2]
            cx1, cx2 = np.clip([x1, x2], 0, width).astype(int)
            cy1, cy2 = np.clip([y1, y2], 0, height).astype(int)
            if cx2 <= cx1 or cy2 <= cy1: continue
            crop = cv2.cvtColor(frame[cy1:cy2, cx1:cx2], cv2.COLOR_BGR2RGB)
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=crop.astype(np.uint8))
            result = detector.detect_for_video(image, int((start_frame + local_index) / fps * 1000))
            match = None
            requested = "Right" if requested_right else "Left"
            for index, handedness in enumerate(result.handedness):
                if handedness and handedness[0].category_name == requested:
                    match = index; break
            if match is None or match >= len(result.hand_world_landmarks): continue
            world = result.hand_world_landmarks[match]
            image_landmarks = result.hand_landmarks[match]
            raw[local_index] = np.asarray([[p.x,p.y,p.z] for p in world], dtype=np.float32)
            projected[local_index] = np.asarray([
                [cx1 + p.x * (cx2-cx1), cy1 + p.y * (cy2-cy1)]
                for p in image_landmarks], dtype=np.float32)
            detected += 1
    finally:
        cap.release(); detector.close()

    coverage = detected / max(1, expected)
    rejected = {"engine":"mediapipe_world_landmarks","accepted":False,
                "requires_verification":True,"coverage":coverage,"reasons":[]}
    if expected < 3 or coverage < 0.95:
        rejected["reasons"].append("MediaPipe hand coverage below 95%")
        return rejected
    try:
        raw = _interpolate_track(raw); projected = _interpolate_track(projected)
        final, corrected, diagnostics, quality = process_landmarks(raw)
    except Exception as exc:
        rejected["reasons"].append(f"MediaPipe processing failed: {exc}")
        return rejected

    reasons = []
    if not quality.get("pass"): reasons.append("Deterministic trajectory checks failed")
    if quality.get("low_confidence_fraction", 1) > 0.05: reasons.append("More than 5% low-confidence frames")
    if quality.get("max_landmark_step", 99) > 0.30: reasons.append("Implausible landmark discontinuity")
    if not 15 <= quality.get("robust_range_deg", 0) <= 320: reasons.append("Implausible P/S range")
    if quality.get("p99_angle_step_deg", 99) > 45: reasons.append("Implausible angle step")
    accepted = not reasons
    return {"engine":"mediapipe_world_landmarks","accepted":accepted,
            "requires_verification":True,"coverage":coverage,"reasons":reasons,
            "raw":raw if accepted else None,"projected":projected if accepted else None,
            "corrected":corrected if accepted else None,"final":final if accepted else None,
            "diagnostics":diagnostics if accepted else None,"quality":quality}
