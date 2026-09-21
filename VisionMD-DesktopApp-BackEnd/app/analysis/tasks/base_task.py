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
                lm.z, 
            ])
        return coords

    @staticmethod
    def interpolate_missing_landmarks_old(landmarks):
        """
        Linearly interpolates missing landmark frames using np.interp.

        Input format:
            landmarks[frame_index][landmark_index][coord_index]

        Notes:
            - Supports either 2D points ([x, y]) or 3D points ([x, y, z]).
            - Missing frames are expected to be [] or None.
            - Leading/trailing gaps are filled with the nearest valid value.
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
        num_frames_missing = 0
        frame_indices = np.arange(num_frames, dtype=float)
        interpolated = np.full((num_frames, num_landmarks, num_coords), np.nan, dtype=float)

        for frame_index, frame in enumerate(landmarks):
            if frame is None or frame == []:
                num_frames_missing += 1
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
                    interpolated[frame_index, landmark_index, :] = np.asarray(point, dtype=float)
                except Exception as exc:
                    raise ValueError(f"Non-numeric coordinate at frame {frame_index}, landmark {landmark_index}.") from exc

        for landmark_index in range(num_landmarks):
            for coord_index in range(num_coords):
                series = interpolated[:, landmark_index, coord_index]
                valid_mask = np.isfinite(series)
                valid_count = int(np.sum(valid_mask))

                if valid_count == 0:
                    raise ValueError(
                        f"No valid values for landmark {landmark_index}, coordinate {coord_index}."
                    )

                valid_x = frame_indices[valid_mask]
                valid_y = series[valid_mask]

                if valid_count == 1:
                    series[:] = valid_y[0]
                else:
                    series[:] = np.interp(frame_indices, valid_x, valid_y)

                interpolated[:, landmark_index, coord_index] = series

        print(f"Number of missing frames where landmarks were interpolated: {num_frames_missing}")
        return interpolated.tolist()


    @staticmethod
    def interpolate_missing_landmarks(
        landmarks,
        smooth=True,
        reject_outliers=False,
        process_noise=3e-2,
        measurement_noise=4e-2,
        gate_sigma=4.0,
        verbose=True,
    ):
        """
        Fill missing landmark frames with a constant-velocity Kalman/RTS smoother
        instead of linear interpolation.

        Drop-in replacement for the old np.interp version: same input/output format.

            landmarks[frame_index][landmark_index][coord_index]

        Missing frames are [] or None. Supports 2D ([x, y]) or 3D ([x, y, z]) points.
        Each coordinate of each landmark is treated as an independent 1-D track with
        state [position, velocity]. Gaps are filled by coasting on the estimated
        velocity, and a forward-backward (RTS) pass means the fill is anchored by
        data on both sides, including at the very start and end of the clip.

        Why this beats linear interpolation:
            np.interp draws a straight line across a gap, which flattens any motion
            that was happening (a mid-tap gap becomes a dead segment). The smoother
            carries the estimated motion through the gap instead.

        Parameters
        ----------
        smooth : bool
            True  -> return the smoothed trajectory for every frame (observed frames
                    are denoised too).
            False -> keep observed frames exactly as measured and only replace the
                    missing ones. Closest to the old "only touch the gaps" behaviour.
        reject_outliers : bool
            If True, also drop confidently-wrong measurements. Each frame's error
            against the filter's own prediction is measured in sigma units; anything
            past `gate_sigma` is treated as missing and coasted over. This is what
            catches the "landmark jumped onto a leaf / nearby object" frames that
            MediaPipe reports with full confidence. Off by default so the function
            only fills frames the caller already marked missing.
        process_noise, measurement_noise : float
            Dimensionless. Scaled internally by each track's own robust spread, so
            the same defaults work whether the input is pixels or normalized coords.
            Their ratio controls smoothing: raise process_noise to follow fast
            motion more closely, raise measurement_noise to smooth harder.
        gate_sigma : float
            Rejection threshold when reject_outliers=True. Larger = more permissive.
        verbose : bool
            Print a short summary.

        Returns
        -------
        list
            Same nested-list shape as the input, all frames filled.
        """

        #Kalman smoother for 1D tracks
        def _rts_1d(z, q, r):
            """
            Constant-velocity Kalman filter + RTS smoother on one 1-D track.
    
            z : 1-D array with NaN at missing frames (those frames are coasted over).
            Returns the smoothed position at every frame.
            """
            n = len(z)
            A = np.array([[1.0, 1.0], [0.0, 1.0]])
            H = np.array([[1.0, 0.0]])
            Q = q * np.array([[1 / 3, 1 / 2], [1 / 2, 1.0]])
            R = np.array([[r]])
    
            xf = np.zeros((n, 2))          # filtered state
            Pf = np.zeros((n, 2, 2))       # filtered covariance
            xp = np.zeros((n, 2))          # predicted state (for the smoother)
            Pp = np.zeros((n, 2, 2))       # predicted covariance
    
            # start from the first finite sample, zero initial velocity, loose prior
            first = int(np.argmax(np.isfinite(z)))
            x = np.array([z[first], 0.0])
            P = np.eye(2) * (r + q) * 10.0
    
            for k in range(n):
                xpr = A @ x
                Ppr = A @ P @ A.T + Q
                xp[k], Pp[k] = xpr, Ppr
    
                zk = z[k]
                if not np.isfinite(zk):
                    x, P = xpr, Ppr          # missing -> coast on the motion model
                else:
                    S = H @ Ppr @ H.T + R
                    y = zk - (H @ xpr)[0]
                    K = (Ppr @ H.T) / S[0, 0]
                    x = xpr + (K[:, 0] * y)
                    P = (np.eye(2) - K @ H) @ Ppr
                xf[k], Pf[k] = x, P
    
            # RTS backward pass: every frame corrected using all later frames
            xs = xf.copy()
            for k in range(n - 2, -1, -1):
                C = Pf[k] @ A.T @ np.linalg.inv(Pp[k + 1])
                xs[k] = xf[k] + C @ (xs[k + 1] - xp[k + 1])
    
            return xs[:, 0]


        # ---- validate + find the first valid frame -----------------------------
        first_valid = None
        for frame in landmarks:
            if frame:  # not None and not []
                first_valid = frame
                break
        if first_valid is None:
            raise ValueError("No valid frame found. Cannot process all-missing landmarks.")

        num_landmarks = len(first_valid)
        if num_landmarks == 0:
            raise ValueError("First valid frame has no landmarks.")
        num_coords = len(first_valid[0])
        if num_coords not in (2, 3):
            raise ValueError(f"Coordinate dimension must be 2 or 3, got {num_coords}.")

        num_frames = len(landmarks)
        arr = np.full((num_frames, num_landmarks, num_coords), np.nan, dtype=float)
        num_missing = 0
        for f, frame in enumerate(landmarks):
            if not frame:  # None or []
                num_missing += 1
                continue
            if len(frame) != num_landmarks:
                raise ValueError(
                    f"Frame {f} has {len(frame)} landmarks; expected {num_landmarks}."
                )
            for l, point in enumerate(frame):
                if len(point) != num_coords:
                    raise ValueError(
                        f"Frame {f}, landmark {l} has {len(point)} coords; expected {num_coords}."
                    )
                arr[f, l, :] = np.asarray(point, dtype=float)

        out = arr.copy()
        num_gated = 0

        # ---- filter + smoother, per landmark per coordinate --------------------
        for l in range(num_landmarks):
            for c in range(num_coords):
                series = arr[:, l, c]
                valid = np.isfinite(series)
                n_valid = int(valid.sum())
                if n_valid == 0:
                    raise ValueError(f"No valid values for landmark {l}, coord {c}.")
                if n_valid == 1:
                    out[:, l, c] = series[valid][0]
                    continue

                # per-track scale so one set of noise defaults works at any scale
                vals = series[valid]
                scale = np.median(np.abs(vals - np.median(vals))) * 1.4826  # robust std
                if scale < 1e-9:
                    scale = np.std(vals) if np.std(vals) > 1e-9 else 1.0
                r = (measurement_noise * scale) ** 2
                q = (process_noise * scale) ** 2

                sm = _rts_1d(series, q, r)
                gated = np.zeros(num_frames, dtype=bool)

                if reject_outliers:
                    # data-driven gate: flag frames whose measurement sits far off the
                    # smoothed path, in units of the track's own residual spread. This
                    # adapts to each clip's motion, so real fast taps are not rejected
                    # while a tip that jumped onto a leaf / nearby object is.
                    resid = np.abs(series - sm)
                    r_valid = resid[valid]
                    rscale = np.median(r_valid) * 1.4826
                    if rscale < 1e-9:
                        rscale = np.std(r_valid) if np.std(r_valid) > 1e-9 else scale
                    gated = valid & (resid > gate_sigma * rscale)
                    if gated.any():
                        # re-smooth with the outliers removed so they don't drag the fit
                        cleaned = series.copy()
                        cleaned[gated] = np.nan
                        sm = _rts_1d(cleaned, q, r)
                    num_gated += int(gated.sum())

                if smooth:
                    out[:, l, c] = sm
                else:
                    # keep measured values, fill only the holes (and gated frames)
                    fill = (~valid) | gated
                    out[fill, l, c] = sm[fill]

        if verbose:
            msg = f"Filled {num_missing} missing frame(s) with RTS smoother"
            if reject_outliers:
                msg += f"; rejected {num_gated} outlier measurement(s)"
            print(msg + ".")

        return out.tolist()

    




    @staticmethod
    def interpolate_missing_landmarks2(
        landmarks,
        smooth=False,
        reject_outliers=False,
        process_noise=3e-2,
        measurement_noise=4e-2,
        gate_sigma=6.0,
        verbose=True,
    ):
        """
        Fill missing landmark frames with a constant-velocity Kalman/RTS smoother
        instead of linear interpolation.

        Drop-in replacement for the old np.interp version: same input/output format.

            landmarks[frame_index][landmark_index][coord_index]

        Missing frames are [] or None. Supports 2D ([x, y]) or 3D ([x, y, z]) points.
        Each coordinate of each landmark is treated as an independent 1-D track with
        state [position, velocity]. Gaps are filled by coasting on the estimated
        velocity, and a forward-backward (RTS) pass means the fill is anchored by
        data on both sides, including at the very start and end of the clip.

        Why this beats linear interpolation:
            np.interp draws a straight line across a gap, which flattens any motion
            that was happening (a mid-tap gap becomes a dead segment). The smoother
            carries the estimated motion through the gap instead.

        Parameters
        ----------
        smooth : bool
            True  -> return the smoothed trajectory for every frame (observed frames
                    are denoised too).
            False -> keep observed frames exactly as measured and only replace the
                    missing ones. Closest to the old "only touch the gaps" behaviour.
        reject_outliers : bool
            If True, also drop confidently-wrong measurements. Each frame's error
            against the filter's own prediction is measured in sigma units; anything
            past `gate_sigma` is treated as missing and coasted over. This is what
            catches the "landmark jumped onto a leaf / nearby object" frames that
            MediaPipe reports with full confidence. Off by default so the function
            only fills frames the caller already marked missing.
        process_noise, measurement_noise : float
            Dimensionless. Scaled internally by each track's own robust spread, so
            the same defaults work whether the input is pixels or normalized coords.
            Their ratio controls smoothing: raise process_noise to follow fast
            motion more closely, raise measurement_noise to smooth harder.
        gate_sigma : float
            Rejection threshold when reject_outliers=True. Larger = more permissive.
        verbose : bool
            Print a short summary.

        Returns
        -------
        list
            Same nested-list shape as the input, all frames filled.
        """


        def _rts_1d(z, q, r):
            """
            Constant-velocity Kalman filter + RTS smoother on one 1-D track.

            z : 1-D array with NaN at missing frames (those frames are coasted over).
            Returns the smoothed position at every frame.
            """
            n = len(z)
            A = np.array([[1.0, 1.0], [0.0, 1.0]])
            H = np.array([[1.0, 0.0]])
            Q = q * np.array([[1 / 3, 1 / 2], [1 / 2, 1.0]])
            R = np.array([[r]])

            xf = np.zeros((n, 2))          # filtered state
            Pf = np.zeros((n, 2, 2))       # filtered covariance
            xp = np.zeros((n, 2))          # predicted state (for the smoother)
            Pp = np.zeros((n, 2, 2))       # predicted covariance

            # start from the first finite sample, zero initial velocity, loose prior
            first = int(np.argmax(np.isfinite(z)))
            x = np.array([z[first], 0.0])
            P = np.eye(2) * (r + q) * 10.0

            for k in range(n):
                xpr = A @ x
                Ppr = A @ P @ A.T + Q
                xp[k], Pp[k] = xpr, Ppr

                zk = z[k]
                if not np.isfinite(zk):
                    x, P = xpr, Ppr          # missing -> coast on the motion model
                else:
                    S = H @ Ppr @ H.T + R
                    y = zk - (H @ xpr)[0]
                    K = (Ppr @ H.T) / S[0, 0]
                    x = xpr + (K[:, 0] * y)
                    P = (np.eye(2) - K @ H) @ Ppr
                xf[k], Pf[k] = x, P

            # RTS backward pass: every frame corrected using all later frames
            xs = xf.copy()
            for k in range(n - 2, -1, -1):
                C = Pf[k] @ A.T @ np.linalg.inv(Pp[k + 1])
                xs[k] = xf[k] + C @ (xs[k + 1] - xp[k + 1])

            return xs[:, 0]
        
        # ---- validate + find the first valid frame -----------------------------
        first_valid = None
        for frame in landmarks:
            if frame:  # not None and not []
                first_valid = frame
                break
        if first_valid is None:
            raise ValueError("No valid frame found. Cannot process all-missing landmarks.")

        num_landmarks = len(first_valid)
        if num_landmarks == 0:
            raise ValueError("First valid frame has no landmarks.")
        num_coords = len(first_valid[0])
        if num_coords not in (2, 3):
            raise ValueError(f"Coordinate dimension must be 2 or 3, got {num_coords}.")

        num_frames = len(landmarks)
        arr = np.full((num_frames, num_landmarks, num_coords), np.nan, dtype=float)
        num_missing = 0
        for f, frame in enumerate(landmarks):
            if not frame:  # None or []
                num_missing += 1
                continue
            if len(frame) != num_landmarks:
                raise ValueError(
                    f"Frame {f} has {len(frame)} landmarks; expected {num_landmarks}."
                )
            for l, point in enumerate(frame):
                if len(point) != num_coords:
                    raise ValueError(
                        f"Frame {f}, landmark {l} has {len(point)} coords; expected {num_coords}."
                    )
                arr[f, l, :] = np.asarray(point, dtype=float)

        out = arr.copy()
        num_gated = 0

        # ---- filter + smoother, per landmark per coordinate --------------------
        for l in range(num_landmarks):
            for c in range(num_coords):
                series = arr[:, l, c]
                valid = np.isfinite(series)
                n_valid = int(valid.sum())
                if n_valid == 0:
                    raise ValueError(f"No valid values for landmark {l}, coord {c}.")
                if n_valid == 1:
                    out[:, l, c] = series[valid][0]
                    continue

                # per-track scale so one set of noise defaults works at any scale
                vals = series[valid]
                scale = np.median(np.abs(vals - np.median(vals))) * 1.4826  # robust std
                if scale < 1e-9:
                    scale = np.std(vals) if np.std(vals) > 1e-9 else 1.0
                r = (measurement_noise * scale) ** 2
                q = (process_noise * scale) ** 2

                sm = _rts_1d(series, q, r)
                gated = np.zeros(num_frames, dtype=bool)

                if reject_outliers:
                    # data-driven gate: flag frames whose measurement sits far off the
                    # smoothed path, in units of the track's own residual spread. This
                    # adapts to each clip's motion, so real fast taps are not rejected
                    # while a tip that jumped onto a leaf / nearby object is.
                    resid = np.abs(series - sm)
                    r_valid = resid[valid]
                    rscale = np.median(r_valid) * 1.4826
                    if rscale < 1e-9:
                        rscale = np.std(r_valid) if np.std(r_valid) > 1e-9 else scale
                    gated = valid & (resid > gate_sigma * rscale)
                    if gated.any():
                        # re-smooth with the outliers removed so they don't drag the fit
                        cleaned = series.copy()
                        cleaned[gated] = np.nan
                        sm = _rts_1d(cleaned, q, r)
                    num_gated += int(gated.sum())

                if smooth:
                    out[:, l, c] = sm
                else:
                    # keep measured values, fill only the holes (and gated frames)
                    fill = (~valid) | gated
                    out[fill, l, c] = sm[fill]

        if verbose:
            msg = f"Filled {num_missing} missing frame(s) with RTS smoother"
            if reject_outliers:
                msg += f"; rejected {num_gated} outlier measurement(s)"
            print(msg + ".")

        return out.tolist()



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



    @staticmethod
    def clean_display_track(
        landmarks,
        task="hand_movement",
        # cross-finger geometry (sustained grabs)
        geom_margin=0.35,
        geom_closed_below=0.60,
        geom_min_run=2,
        # per-finger spike detector (one-off flicks)
        spike_window=7,
        spike_k=6.0,
        null_mcp=True,
        return_mask=False,
    ):
        """
        Produce a clean landmark track for on-screen display in VisionMD.

        Two detectors run on the raw landmarks and both feed the same
        per-finger null-then-linear-interpolate step:

        1. Cross-finger geometry  -> sustained object-confusion grabs (multi-frame
            runs where one finger reads extended while the hand is closed). HAND
            MOVEMENT ONLY: in finger tapping the index legitimately extends alone,
            so this detector is skipped for that task.
        2. Per-finger spike test  -> one-off frames where a single fingertip flicks
            off its own smooth path for a frame or two. Task-agnostic.

        Nulling is per finger, so only the finger that is actually wrong is
        replaced; the others pass through untouched. Filling is plain linear
        interpolation (the validated filler) over each affected coordinate.

        IMPORTANT: this is the DISPLAY track. On a corrected run the finger shown is
        an interpolated reconstruction, not the observed motion. Keep the raw track
        for the score unless you have re-validated corrected input against your
        annotations.

        Parameters
        ----------
        landmarks : nested list or array, shape (F, 21, 2 or 3)
        task : str
            "hand_movement" enables the geometry detector; anything else skips it
            and uses only the per-finger spike test.
        geom_margin, geom_closed_below, geom_min_run :
            Geometry-detector thresholds (see detect notes above).
        spike_window : int
            Half-window for the per-finger robust spike test.
        spike_k : float
            Spike threshold in robust-sigma units. Higher = fewer flags.
        null_mcp : bool
            Null the whole finger chain (True) or keep the mcp anchor (False).
        return_mask : bool
            Also return the per-landmark bad mask and a per-detector report.

        Returns
        -------
        clean : list, shape (F, 21, C)   nested list, ready for display
        (optional) bad_mask : np.ndarray (F, 21) bool
        (optional) report : dict
        """
        #useful functions and definitions
        # MediaPipe hand: each long finger as (mcp, pip, dip, tip)
        _FINGERS = {
            "index":  (5, 6, 7, 8),
            "middle": (9, 10, 11, 12),
            "ring":   (13, 14, 15, 16),
            "pinky":  (17, 18, 19, 20),
        }
        _LONG = ["index", "middle", "ring", "pinky"]

        def _spike_mask(x, w, k, max_len=3):
            """
            Transient-spike test: flag a short run only if it departs from the signal
            AND the signal returns to the same level afterwards. This rejects steps
            (a fast move to a new level that holds), which a plain median/Hampel test
            would wrongly flag at the transition.

            A candidate frame deviates from its local robust median. Candidates are
            grouped into runs; a run is a genuine spike when the baseline just before
            it and just after it agree (the signal came back) and the run stands off
            that shared baseline. A run that separates two different baselines is a
            step and is left alone.
            """
            from numpy.lib.stride_tricks import sliding_window_view
            F = len(x)
            pad = np.pad(x, w, mode="edge")
            win = sliding_window_view(pad, 2 * w + 1)
            med = np.median(win, axis=1)
            mad = np.median(np.abs(win - med[:, None]), axis=1) * 1.4826
            scale = np.maximum(np.median(mad[mad > 0]) if (mad > 0).any() else 1e-6, 1e-6)
            cand = np.abs(x - med) > k * np.maximum(mad, 1e-6)

            out = np.zeros(F, dtype=bool)
            fr = np.where(cand)[0]
            if len(fr) == 0:
                return out
            # group candidates into runs
            runs, s, p = [], fr[0], fr[0]
            for q in list(fr[1:]) + [None]:
                if q == p + 1:
                    p = q
                else:
                    runs.append((s, p)); 
                    if q is not None:
                        s = p = q
            for s, e in runs:
                if (e - s + 1) > max_len:
                    continue  # too long to be a transient spike; a sustained grab, not this detector's job
                b0 = np.median(x[max(0, s - w):s]) if s > 0 else x[e + 1] if e + 1 < F else x[s]
                b1 = np.median(x[e + 1:e + 1 + w]) if e + 1 < F else b0
                run_dev = np.max(np.abs(x[s:e + 1] - 0.5 * (b0 + b1)))
                returned = np.abs(b0 - b1) < 0.5 * run_dev      # baselines agree -> came back
                stands_off = run_dev > k * scale                 # run clearly off the baseline
                if returned and stands_off:
                    out[s:e + 1] = True
            return out


        def _keep_runs(mask, min_run):
            """Keep only runs of at least min_run consecutive True frames."""
            F = len(mask)
            kept = np.zeros(F, dtype=bool)
            runs = []
            fr = np.where(mask)[0]
            if len(fr) == 0:
                return kept, runs
            s = p = fr[0]
            for q in list(fr[1:]) + [None]:
                if q == p + 1:
                    p = q
                else:
                    if (p - s + 1) >= min_run:
                        kept[s:p + 1] = True
                        runs.append((int(s), int(p), int(p - s + 1)))
                    if q is not None:
                        s = p = q
            return kept, runs


        def _null_finger(bad_mask, name, frames_mask, null_mcp):
            idxs = _FINGERS[name] if null_mcp else _FINGERS[name][1:]
            for j in idxs:
                bad_mask[frames_mask, j] = True


        A = np.asarray(landmarks, dtype=float)
        if A.ndim != 3 or A.shape[1] != 21:
            raise ValueError(f"Expected (F, 21, 2 or 3); got {A.shape}.")
        F, _, C = A.shape

        scale = np.linalg.norm(A[:, 9, :2] - A[:, 0, :2], axis=1)
        good = scale > 1e-6
        scale = np.where(good, scale, np.median(scale[good]) if good.any() else 1.0)

        # extension (tip-to-mcp) and reach (tip-to-wrist), per long finger, normalized
        ext = {n: np.linalg.norm(A[:, t, :2] - A[:, m, :2], axis=1) / scale
            for n, (m, _, _, t) in _FINGERS.items()}
        reach = {n: np.linalg.norm(A[:, _FINGERS[n][3], :2] - A[:, 0, :2], axis=1) / scale
                for n in _LONG}

        bad_mask = np.zeros((F, 21), dtype=bool)
        report = {"geometry": {}, "spike": {}}

        # ---- 1. cross-finger geometry (Hand Movement only) ----
        if task == "hand_movement":
            E = np.stack([ext[n] for n in _LONG], axis=1)
            for i, name in enumerate(_LONG):
                med_others = np.median(np.delete(E, i, axis=1), axis=1)
                suspect = (E[:, i] - med_others > geom_margin) & (med_others < geom_closed_below)
                kept, runs = _keep_runs(suspect, geom_min_run)
                _null_finger(bad_mask, name, kept, null_mcp)
                report["geometry"][name] = runs

        # ---- 2. per-finger one-off spikes (all tasks) ----
        for name in _LONG:
            sp = _spike_mask(reach[name], spike_window, spike_k)
            _null_finger(bad_mask, name, sp, null_mcp)
            report["spike"][name] = np.where(sp)[0].tolist()

        # ---- 3. per-landmark linear interpolation over flagged frames ----
        clean = A.copy()
        t = np.arange(F)
        for j in range(21):
            bad_j = bad_mask[:, j]
            if not bad_j.any():
                continue
            keep = ~bad_j
            if keep.sum() < 2:
                continue  # not enough anchors; leave as-is
            for c in range(C):
                clean[bad_j, j, c] = np.interp(t[bad_j], t[keep], clean[keep, j, c])

        if return_mask:
            return clean.tolist(), bad_mask, report
        return clean.tolist()

    # ------------------------------------------------
    # --- END: Utility functions as static methods ---
    # ------------------------------------------------