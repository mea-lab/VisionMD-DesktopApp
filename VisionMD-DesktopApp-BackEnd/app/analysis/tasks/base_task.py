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