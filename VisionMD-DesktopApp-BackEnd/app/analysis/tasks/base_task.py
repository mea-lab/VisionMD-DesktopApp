# tasks/base_task.py

import cv2
import mediapipe as mp
import numpy as np
import math
import os, uuid, time, json, traceback
from django.core.files.storage import FileSystemStorage
from abc import ABC, abstractmethod
from pymediainfo import MediaInfo
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata

class BaseTask(ABC):
    """
    Base class for all tasks (hand movement, finger tap, leg agility, toe tapping, etc.)
    Each concrete subclass must implement these abstract methods for retrieving
    & processing landmarks.
    """

    # ------------------------------------------------------------------
    # --- START: Abstract properties to be implemented by subclasses ---
    # ------------------------------------------------------------------
    @property
    def LANDMARKS(self):
        """
        Should be a dictionary where each landmark
        constant (e.g., WRIST, THUMB_TIP) maps to its corresponding index.
        """
        pass

    # ----------------------------------------------------------------
    # --- END: Abstract properties to be implemented by subclasses ---
    # ----------------------------------------------------------------





    # ---------------------------------------------------------------
    # --- START: Abstract methods to be implemented by subclasses ---
    # ---------------------------------------------------------------
    @abstractmethod
    def __init__(self):
        """
        Function that should declare all instance attributes which are the video parameters.
        Below we have provided an example of a set of instance attributes you may want to declare.
        """
        self.video_id = None
        self.video_fps = None
        self.video_rotation = None
        self.video_file_path = None
        self.video_file_name = None

        self.task_name = None
        self.task_start_time = None
        self.task_end_time = None
        self.task_start_frame_idx = None
        self.task_end_frame_idx = None

        self.original_bounding_box = None
        self.enlarged_bounding_box = None
        self.subject_bounding_boxes = None

    @abstractmethod
    def api_response(self, request):
        """
        Function that handles the api response for each task
        """
        pass

    
    @abstractmethod
    def prepare_video_parameters(self, request):
        """
        Prepares video parameters from the HTTP request:
         - Parses JSON for bounding box and time codes.
         - Saves the uploaded video file.
         - Computes the expanded bounding box.
         - Determines FPS and start/end frame indices.
        Returns a dictionary of parameters. 
        MUST DEFINE ALL INSTANCE ATTRIBUTES DECLARED IN INIT. 
        """
        pass


    @abstractmethod 
    def get_detector(self) -> object:
        """
        Getter for the detector used by the task.

        Returns an instance of the detector using the detectors classes
        """
        pass


    @abstractmethod
    def get_signal_analyzer(self) -> object:
        """
        Getter for the signal analyzer used by the task

        Returns an instance of the signal analyze using the analyzer classes
        """
        pass


    @abstractmethod
    def calculate_signal(self, essential_landmarks) -> list:
        """
        Given a set of display landmarks (one list per frame), return the raw 1D
        signal array.
        """
        pass

    @abstractmethod
    def extract_landmarks(self, detector) -> tuple:
        """
        Process video frames between start_frame and end_frame and extract hand landmarks 
        for the left hand from each frame.
        
        Returns:
            tuple: (essential_landmarks, all_landmarks)
            - essential_landmarks: a list of lists where each inner list contains the key landmark coordinates for that frame.
            - all_landmarks: a list of lists containing all the landmark coordinates for that frame.
        """
        pass


    @abstractmethod
    def calculate_normalization_factor(self, essential_landmarks) -> float:
        """
        Return a caluclated scalar factor used to normalize the raw 1D signal.
        """
        pass
    # -------------------------------------------------------------
    # --- END: Abstract methods to be implemented by subclasses ---
    # -------------------------------------------------------------





    # --------------------------------------------------
    # --- START: Utility functions as static methods ---
    # --------------------------------------------------
    @staticmethod
    def get_landmark_coords(landmark, enlarged_coords, original_coords):
        """
        Computes the (x, y) coordinates of a given landmark relative to the provided bounds.
        """
        x1, y1, x2, y2 = enlarged_coords
        ox1, oy1, ox2, oy2 = original_coords
        return [
            landmark.x * (x2 - x1) +  x1,
            landmark.y * (y2 - y1) +  y1,
        ]

    @staticmethod
    def get_all_landmarks_coord(landmarks, enlarged_coords, original_coords):
        """
        Processes a list of landmarks and returns their (x, y, z) coordinates relative
        to the provided bounds.
        """
        x1, y1, x2, y2 = enlarged_coords
        ox1, oy1, ox2, oy2 = original_coords
        coords = []
        for lm in landmarks:
            coords.append([
                lm.x * (x2 - x1) + x1,
                lm.y * (y2 - y1) + y1,
                lm.z
            ])
        return coords

    @staticmethod
    def interpolate_missing_landmarks(landmarks):
        """Backward-compatible wrapper for :meth:`repair_landmark_track`.

        Despite the historical name, this no longer smooths every measurement.
        Valid observations are kept exactly as MediaPipe returned them.  Only
        missing observations and short, isolated temporal outliers are replaced.
        """
        repaired, _ = BaseTask.repair_landmark_track(landmarks, return_quality=True)
        return repaired

    @staticmethod
    def repair_landmark_track(
        landmarks,
        fps=30.0,
        reject_outliers=True,
        max_outlier_run_seconds=0.12,
        return_quality=False,
    ):
        """Repair missing or implausible landmarks without smoothing valid data.

        The operation deliberately has two separate stages:

        1. A landmark is labelled as an outlier only when it is a *short* spike
           relative to both neighbouring frames.  The displacement is divided by
           the subject/hand scale in that frame, so this works for both normalized
           MediaPipe coordinates and pixel coordinates.  Long runs are never
           silently classified as spikes; they are reported for quality control.
        2. Missing values and rejected spikes are estimated with a constant-
           velocity Kalman filter followed by an RTS backward pass.  The original
           values are then restored at every observed location.  Consequently the
           Kalman pass fills gaps; it does not low-pass or otherwise change valid
           measurements.  Signal smoothing remains the responsibility of each
           task's signal-processing pipeline.

        ``quality`` contains masks and counts that callers may expose in their JSON
        output.  Existing callers receive only the repaired list, preserving the
        old ``interpolate_missing_landmarks`` contract.
        """

        # Error Checking
        first_valid_frame = None
        num_landmarks = None
        num_coords = None
        for frame_index, frame in enumerate(landmarks):
            if frame is None:
                continue
            if len(frame) > 0:
                first_valid_frame = frame
                num_landmarks = len(first_valid_frame)
                num_coords = len(first_valid_frame[0])
                break
        if first_valid_frame is None:
            raise ValueError("No valid frame found. Cannot interpolate all-missing landmarks.")
        if num_landmarks == 0:
            raise ValueError("First valid frame has no landmarks.")
        if num_coords not in (2, 3):
            raise ValueError(f"Landmark coordinate dimension must be 2 or 3, got {num_coords}.")
        for landmark_index, point in enumerate(first_valid_frame):
            if not isinstance(point, list):
                raise TypeError(f"First valid frame landmark {landmark_index} is not a coordinate list.")
            if len(point) != num_coords:
                raise ValueError("Inconsistent coordinate dimension in first valid frame.")

        num_frames = len(landmarks)
        values = np.full((num_frames, num_landmarks, num_coords), np.nan, dtype=float)
        missing_frame_mask = np.zeros(num_frames, dtype=bool)

        for frame_index, frame in enumerate(landmarks):
            if frame is None or frame == []:
                missing_frame_mask[frame_index] = True
                continue
            if not isinstance(frame, list):
                raise TypeError(f"Frame {frame_index} must be a list, [] for missing, or None.")
            if len(frame) != num_landmarks:
                raise ValueError(f"Frame {frame_index} has {len(frame)} landmarks; expected {num_landmarks}.")

            for landmark_index, point in enumerate(frame):
                if not isinstance(point, list):
                    raise TypeError(f"Frame {frame_index}, landmark {landmark_index} is not a coordinate list.")
                if len(point) != num_coords:
                    raise ValueError(f"Frame {frame_index}, landmark {landmark_index} has {len(point)} coords, expected {num_coords}.")
                try:
                    values[frame_index, landmark_index, :] = np.asarray(point, dtype=float)
                except Exception as exc:
                    raise ValueError(f"Non-numeric coordinate at frame {frame_index}, landmark {landmark_index}.") from exc

        original_valid = np.all(np.isfinite(values), axis=2)
        outlier_mask = np.zeros((num_frames, num_landmarks), dtype=bool)
        long_outlier_mask = np.zeros_like(outlier_mask)

        if reject_outliers and num_frames >= 3:
            # Robust per-frame subject scale.  It avoids fixed pixel/normalized
            # thresholds and is intentionally independent of landmark identity.
            centers = np.nanmedian(values, axis=1, keepdims=True)
            scale = np.nanmedian(np.linalg.norm(values - centers, axis=2), axis=1)
            finite_scale = scale[np.isfinite(scale) & (scale > 1e-9)]
            fallback_scale = float(np.median(finite_scale)) if finite_scale.size else 1.0
            scale = np.where(np.isfinite(scale) & (scale > 1e-9), scale, fallback_scale)

            midpoint = 0.5 * (values[:-2] + values[2:])
            residual = np.linalg.norm(values[1:-1] - midpoint, axis=2)
            local_scale = np.maximum(scale[1:-1, None], 1e-9)
            normalized = residual / local_scale
            neighbor_change = np.linalg.norm(values[2:] - values[:-2], axis=2) / local_scale
            finite_residual = normalized[np.isfinite(normalized)]
            if finite_residual.size:
                med = float(np.median(finite_residual))
                mad = float(np.median(np.abs(finite_residual - med)))
                threshold = max(0.20, med + 8.0 * 1.4826 * mad)
                candidates = np.zeros_like(outlier_mask)
                candidates[1:-1] = (
                    (normalized > threshold)
                    # A true isolated spike returns to approximately the same
                    # trajectory.  If the neighbours disagree strongly this may
                    # instead be sustained real motion (or a long bad run), which
                    # cannot be resolved safely without detector confidence.
                    & (neighbor_change < max(0.20, threshold * 0.75))
                    & original_valid[:-2]
                    & original_valid[1:-1]
                    & original_valid[2:]
                )

                max_run = max(1, int(round(float(fps or 30.0) * max_outlier_run_seconds)))
                for landmark_index in range(num_landmarks):
                    indices = np.flatnonzero(candidates[:, landmark_index])
                    for run in np.split(indices, np.where(np.diff(indices) > 1)[0] + 1):
                        if not len(run):
                            continue
                        target = outlier_mask if len(run) <= max_run else long_outlier_mask
                        target[run, landmark_index] = True

        repaired_input = values.copy()
        repaired_input[outlier_mask] = np.nan
        repaired = repaired_input.copy()
        filled_mask = ~np.all(np.isfinite(repaired_input), axis=2)

        for landmark_index in range(num_landmarks):
            for coord_index in range(num_coords):
                series = repaired_input[:, landmark_index, coord_index]
                if not np.any(np.isfinite(series)):
                    raise ValueError(
                        f"No valid values for landmark {landmark_index}, coordinate {coord_index}."
                    )
                repaired[:, landmark_index, coord_index] = BaseTask._rts_fill_series(series)

        quality = {
            "missing_frame_count": int(missing_frame_mask.sum()),
            "rejected_outlier_count": int(outlier_mask.sum()),
            "long_suspicious_run_count": int(long_outlier_mask.sum()),
            "filled_landmark_count": int(filled_mask.sum()),
            "missing_frame_mask": missing_frame_mask.tolist(),
            "outlier_landmark_mask": outlier_mask.tolist(),
            "long_suspicious_landmark_mask": long_outlier_mask.tolist(),
        }
        print(
            "Landmark repair: "
            f"{quality['missing_frame_count']} missing frames, "
            f"{quality['rejected_outlier_count']} short outliers replaced"
        )
        result = repaired.tolist()
        return (result, quality) if return_quality else result

    @staticmethod
    def _rts_fill_series(series):
        """Fill NaNs with a constant-velocity Kalman/RTS estimate.

        Observed samples are copied back unchanged at the end.  This is the key
        distinction between gap filling and signal smoothing in VisionMD.
        """
        observations = np.asarray(series, dtype=float)
        observed = np.isfinite(observations)
        if observed.sum() == 1:
            return np.full_like(observations, observations[observed][0])

        diffs = np.diff(observations[observed])
        measurement_var = float(np.nanmedian(np.abs(diffs - np.nanmedian(diffs))) ** 2)
        measurement_var = max(measurement_var, 1e-6)
        process_var = max(measurement_var * 0.05, 1e-8)

        transition = np.array([[1.0, 1.0], [0.0, 1.0]])
        observation = np.array([[1.0, 0.0]])
        process_noise = process_var * np.array([[0.25, 0.5], [0.5, 1.0]])
        measurement_noise = np.array([[measurement_var]])

        first = int(np.flatnonzero(observed)[0])
        state = np.array([observations[first], 0.0])
        covariance = np.eye(2) * max(measurement_var, 1.0)
        filtered_state = np.zeros((len(observations), 2))
        filtered_cov = np.zeros((len(observations), 2, 2))
        predicted_state = np.zeros_like(filtered_state)
        predicted_cov = np.zeros_like(filtered_cov)

        for index, value in enumerate(observations):
            pred_state = transition @ state
            pred_cov = transition @ covariance @ transition.T + process_noise
            predicted_state[index], predicted_cov[index] = pred_state, pred_cov
            if observed[index]:
                innovation = value - (observation @ pred_state).item()
                innovation_cov = observation @ pred_cov @ observation.T + measurement_noise
                gain = pred_cov @ observation.T @ np.linalg.inv(innovation_cov)
                state = pred_state + gain[:, 0] * innovation
                covariance = (np.eye(2) - gain @ observation) @ pred_cov
            else:
                state, covariance = pred_state, pred_cov
            filtered_state[index], filtered_cov[index] = state, covariance

        smoothed_state = filtered_state.copy()
        for index in range(len(observations) - 2, -1, -1):
            smoother_gain = (
                filtered_cov[index]
                @ transition.T
                @ np.linalg.pinv(predicted_cov[index + 1])
            )
            smoothed_state[index] += smoother_gain @ (
                smoothed_state[index + 1] - predicted_state[index + 1]
            )

        filled = smoothed_state[:, 0]
        filled[observed] = observations[observed]
        return filled

    @staticmethod
    def correct_frame_orientation(cv2_frame, rotation):
        rotation_code = {
            90: cv2.ROTATE_90_CLOCKWISE,
            180: cv2.ROTATE_180,
            270: cv2.ROTATE_90_COUNTERCLOCKWISE
        }.get(rotation, None)
        frame = cv2_frame
        if rotation_code is not None:
            frame = cv2.rotate(cv2_frame, rotation_code)
        return frame

    @staticmethod
    def get_video_width_height(video_file_path, rotation):
        cap = cv2.VideoCapture(video_file_path)
        ret, first_frame = cap.read()
        if not ret:
            cap.release()
            raise Exception("Could not read first frame from video.")
        upright_frame = BaseTask.correct_frame_orientation(first_frame, rotation)
        video_height, video_width = upright_frame.shape[:2]
        cap.release()
        return video_width, video_height
    # ------------------------------------------------
    # --- END: Utility functions as static methods ---
    # ------------------------------------------------
