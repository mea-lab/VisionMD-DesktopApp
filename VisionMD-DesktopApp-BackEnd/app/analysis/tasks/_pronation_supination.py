"""Shared WiLoR implementation for the two pronation/supination tasks.

Pronation/supination is a rotation around the forearm, so a 2-D hand tracker
cannot measure it robustly. WiLoR reconstructs a 3-D hand for every frame.
The signal is the index-MCP-to-pinky-MCP direction, projected perpendicular to
the wrist-to-middle-MCP axis.

Each saved essential landmark is ``[display_x, display_y, world_x, world_y,
world_z]``. VisionMD draws x/y on the video and reuses cached 3-D points for
subrange re-analysis without rerunning WiLoR.
"""

import json
import math
import os

import cv2
import numpy as np
import torch
from django.conf import settings
from rest_framework.response import Response

from .base_task import BaseTask
from app.analysis.models.wilor_mini.pipelines.wilor_hand_pose3d_estimation_pipeline import WiLorHandPose3dEstimationPipeline
from app.analysis.signal_analyzers.peakfinder_signal_analyzer import PeakfinderSignalAnalyzer


_WILOR_MODEL = None


def _get_wilor_model():
    """Load the large WiLoR model only once per Django worker."""
    global _WILOR_MODEL
    if _WILOR_MODEL is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        kwargs = {"device": device, "verbose": False}
        # Useful for development or a centrally managed model cache.  Normal
        # installations omit this variable and WiLoR downloads its official
        # weights into the vendored package's ignored ``pretrained_models``
        # directory on first use.
        model_dir = os.environ.get("VISIONMD_WILOR_MODEL_DIR")
        if model_dir:
            kwargs["wilor_pretrained_dir"] = model_dir
        _WILOR_MODEL = WiLorHandPose3dEstimationPipeline(**kwargs)
    return _WILOR_MODEL


class HandPronationSupinationTask(BaseTask):
    """Common implementation; concrete subclasses only choose the hand side."""

    LANDMARKS = {"WRIST": 0, "INDEX_MCP": 5, "MIDDLE_MCP": 9, "PINKY_MCP": 17}
    HAND_LABEL = None

    def __init__(self):
        self.video_id = self.video_fps = self.video_rotation = None
        self.video_file_path = self.video_file_name = None
        self.task_name = self.task_norm_strategy = None
        self.task_start_time = self.task_end_time = None
        self.task_start_frame_idx = self.task_end_frame_idx = None
        self.original_bounding_box = self.enlarged_bounding_box = None
        self.subject_bounding_boxes = None

    def api_response(self, request):
        try:
            self.prepare_video_parameters(request)
            essential, all_landmarks = self.extract_landmarks()
            # Essential points contain display and WiLoR 3-D coordinates. The
            # generic repairer handles regular 2-D/3-D display tracks only, so
            # angle interpolation is deliberately done in calculate_signal().
            all_landmarks = self.interpolate_missing_landmarks(all_landmarks)
            results = self.get_signal_analyzer().analyze(
                self.calculate_signal(essential), 1.0,
                self.task_start_time, self.task_end_time,
            )
            return {
                "File name": self.video_file_name, "Task name": self.task_name,
                **results, "landMarks": essential, "allLandMarks": all_landmarks,
                "normalization_factor": 1.0,
            }
        except Exception as exc:
            return Response(str(exc), status=500)

    def prepare_video_parameters(self, request):
        video_id = request.GET.get("id")
        if not video_id:
            raise ValueError("Video project id not provided.")
        try:
            payload = json.loads(request.POST["json_data"])
        except (KeyError, json.JSONDecodeError) as exc:
            raise ValueError("Missing or invalid 'json_data' in POST data.") from exc
        folder = os.path.join(settings.MEDIA_ROOT, "video_uploads", video_id)
        try:
            with open(os.path.join(folder, "metadata.json"), encoding="utf-8") as handle:
                metadata = json.load(handle)["metadata"]
        except OSError as exc:
            raise ValueError("Video metadata file does not exist.") from exc
        self.video_id = video_id
        self.video_fps = float(metadata["fps"])
        self.video_rotation = metadata["rotation"]
        self.video_file_name = metadata["video_name"]
        self.video_file_path = os.path.join(folder, self.video_file_name)
        self.task_name = payload["task_name"]
        self.task_norm_strategy = payload.get("norm_strategy", "NONE")
        self.task_start_time, self.task_end_time = float(payload["start_time"]), float(payload["end_time"])
        self.task_start_frame_idx = round(self.video_fps * self.task_start_time)
        self.task_end_frame_idx = round(self.video_fps * self.task_end_time)
        self.original_bounding_box = payload["boundingBox"]

    def get_detector(self):
        return _get_wilor_model()

    def get_signal_analyzer(self):
        return PeakfinderSignalAnalyzer()

    def _select_hand(self, outputs):
        """Select the requested WiLoR side nearest the selected task box."""
        requested_right = self.HAND_LABEL == "Right"
        matches = [
            item for item in outputs
            if "wilor_preds" in item and bool(round(float(item.get("is_right", -1)))) == requested_right
        ]
        if not matches:
            return None
        box = self.original_bounding_box
        task_center = np.array([box["x"] + box["width"] / 2, box["y"] + box["height"] / 2])
        return min(matches, key=lambda item: np.linalg.norm(
            (np.asarray(item["hand_bbox"][:2]) + np.asarray(item["hand_bbox"][2:])) / 2 - task_center
        ))

    def extract_landmarks(self):
        detector = self.get_detector()
        essential, all_landmarks = [], []
        box = self.original_bounding_box
        video = cv2.VideoCapture(self.video_file_path)
        video.set(cv2.CAP_PROP_POS_FRAMES, self.task_start_frame_idx)
        try:
            for _ in range(self.task_start_frame_idx, self.task_end_frame_idx):
                ok, frame = video.read()
                if not ok:
                    break
                frame = BaseTask.correct_frame_orientation(frame, self.video_rotation)
                hand = self._select_hand(detector.predict(frame, hand_conf=0.05))
                if hand is None:
                    essential.append([]); all_landmarks.append([])
                    continue
                prediction = hand["wilor_preds"]
                projected = np.asarray(prediction["pred_keypoints_2d"][0], dtype=float)
                world = np.asarray(prediction["pred_keypoints_3d"][0], dtype=float)
                essential.append([
                    [float(projected[index, 0] - box["x"]), float(projected[index, 1] - box["y"]),
                     float(world[index, 0]), float(world[index, 1]), float(world[index, 2])]
                    for index in (0, 5, 9, 17)
                ])
                all_landmarks.append([
                    [float(point[0] - box["x"]), float(point[1] - box["y"]), 0.0]
                    for point in projected
                ])
        finally:
            video.release()
        if not essential:
            raise ValueError("No video frames could be read for this task.")
        missing_fraction = sum(not frame for frame in essential) / len(essential)
        if missing_fraction > 0.10:
            raise ValueError(
                f"WiLoR could not localize the {self.HAND_LABEL.lower()} hand in more than 10% of frames. "
                "Verify the subject, task side, and analysis range."
            )
        return essential, all_landmarks

    @staticmethod
    def _orientation(points, previous_normal):
        if len(points) < 4 or any(len(point) < 5 for point in points[:4]):
            return math.nan, previous_normal
        wrist, index, middle, pinky = (np.asarray(point[2:5], dtype=float) for point in points[:4])
        axis = middle - wrist
        axis_norm = np.linalg.norm(axis)
        if axis_norm < 1e-8:
            return math.nan, previous_normal
        axis /= axis_norm
        across = index - pinky
        across -= np.dot(across, axis) * axis
        across_norm = np.linalg.norm(across)
        if across_norm < 1e-8:
            return math.nan, previous_normal
        across /= across_norm
        normal = np.cross(axis, across)
        # WiLoR can emit an equivalent, mirrored palm branch in an edge-on
        # frame. A real hand cannot flip 180 degrees in one frame.
        if previous_normal is not None and np.dot(normal, previous_normal) < 0:
            across, normal = -across, -normal
        reference = np.array([0.0, 1.0, 0.0])
        if abs(np.dot(reference, axis)) > 0.95:
            reference = np.array([0.0, 0.0, 1.0])
        reference -= np.dot(reference, axis) * axis
        reference /= np.linalg.norm(reference)
        angle = np.degrees(np.arctan2(np.dot(across, np.cross(axis, reference)), np.dot(across, reference)))
        return float(angle), normal

    def calculate_signal(self, essential_landmarks):
        previous_normal, values = None, []
        for frame in essential_landmarks:
            angle, previous_normal = self._orientation(frame, previous_normal)
            values.append(angle)
        angles = np.asarray(values, dtype=float)
        available = np.flatnonzero(np.isfinite(angles))
        if not len(available):
            raise ValueError("No valid WiLoR 3-D hand landmarks were available for P/S analysis.")
        angles = np.interp(np.arange(len(angles)), available, angles[available])
        # atan2 is circular. Unwrapping avoids a synthetic +/-180-degree peak.
        return np.degrees(np.unwrap(np.radians(angles))).tolist()

    def calculate_normalization_factor(self, landmarks):
        # This is a degree-valued rotational signal, not a distance measure.
        return 1.0
