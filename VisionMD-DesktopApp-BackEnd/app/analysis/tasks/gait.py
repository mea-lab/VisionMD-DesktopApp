import os
import math
import json
import uuid
import numpy as np
import traceback
from django.core.files.storage import FileSystemStorage
import gc
import cv2
from tqdm import tqdm
import torch
import gc
from PIL import Image
from scipy.signal import savgol_filter
from .base_task import BaseTask
from django.conf import settings
from rest_framework.response import Response

from app.analysis.models.metrabs_pytorch.loader import load_model as load_metrabs_model
from app.analysis.models.gait_transformer.gait_phase_transformer_pytorch import load_default_model, gait_phase_stride_inference



class GaitTask(BaseTask):

    # ------------------------------------------------------------------
    # --- START: Abstract properties definitions
    # ------------------------------------------------------------------
    LANDMARKS = np.array(['htop', 'neck', 'rsho', 'relb', 'rwri', 'lsho',
                            'lelb', 'lwri', 'rhip', 'rkne', 'rank', 'lhip', 
                            'lkne', 'lank', 'pelv', 'spin', 'head'])
        
    skeleton = 'mpi_inf_3dhp_17'
    # Transformer positional encoding depends on video FPS. Keep one warmed
    # model per divider instead of deleting/reloading it after every task.
    _gait_phase_transformers = {}
    _metrabs_detector = None
    _metrabs_joint_order = np.array(['htop', 'neck', 'rsho', 'relb', 'rwri', 'lsho',
                            'lelb', 'lwri', 'rhip', 'rkne', 'rank', 'lhip', 
                            'lkne', 'lank', 'pelv', 'spin', 'head'])
    _gait_phase_joint_order = ['pelv', 'rhip', 'rkne', 'rank', 'lhip', 'lkne', 
                            'lank', 'spin', 'neck', 'head', 'htop', 'lsho', 
                            'lelb', 'lwri', 'rsho', 'relb', 'rwri']
    _gait_phase_order_idx = None
    # ------------------------------------------------------------------
    # --- END: Abstract properties definitions
    # ------------------------------------------------------------------
    




    # -------------------------------------------------------------
    # --- START: Abstract methods definitions
    # -------------------------------------------------------------
    def __init__(self):
            self.video_id = None
            self.file_path = None
            self.ile_name = None
            self.task_name = None
            self.rotation = None

            self.fps = None
            self.start_time = None
            self.start_frame_idx = None
            self.end_time = None
            self.end_frame_idx = None

            self.focal_length = None
            self.height_cm = None

            self.original_bounding_box = None
            self.enlarged_bounding_box = None
            self.subject_bounding_boxes = None
            self._progress = lambda progress, message=None: None
            self._cancelled = lambda: False

    def _check_cancelled(self):
        """Stop promptly at safe boundaries between GPU inference calls."""
        if self._cancelled():
            raise RuntimeError("Analysis cancelled")


    def api_response(self, request):
        """
        Function that handles the api response for each task
        """
        try:
            # 1) Getting video parameters from request
            self.prepare_video_parameters(request)

            # 2) Getting detector and using detector to get landmarks
            self._progress(3, "Loading the gait pose model…")
            self._check_cancelled()
            detector = self.get_detector()
            self._progress(5, "Estimating 3D gait landmarks…")
            landmarks, landmarks_mirrored = self.extract_landmarks(detector)

            # 2) Getting signals
            self._check_cancelled()
            self._progress(78, "Estimating gait phases…")
            phases, strides, signals = self.calculate_signal(landmarks['poses3d'], self.height_cm * 10)
            phases_mirrored, strides_mirrored, signals_mirrored = self.calculate_signal(landmarks_mirrored['poses3d'], self.height_cm * 10)

            # 3) Analyze straight walking.  When a turn is present, exclude the
            # turn itself and pool the individual steps from both directions.
            self._check_cancelled()
            self._progress(90, "Calculating gait measures…")
            signal_analyzer = self.get_signal_analyzer()
            # Use the anatomical labels exactly as MeTRAbs produced them for
            # orientation.  The continuity-based left/right correction used by
            # gait inference can intentionally swap labels as a person turns and
            # would otherwise hide a real 180-degree body rotation.
            turning_metadata = self.detect_turn(landmarks['poses3d_orientation'])
            analysis = self.analyze_straight_walking_segments(
                signal_analyzer,
                phases,
                strides,
                landmarks['poses3d'],
                phases_mirrored,
                strides_mirrored,
                landmarks_mirrored['poses3d'],
                turning_metadata,
            )
            results = analysis["results"]
            results_mirrored = analysis["results_mirrored"]
            gait_event_dic = analysis["gait_event_dic"]
            gait_event_dic_mirrored = analysis["gait_event_dic_mirrored"]
            avg_results = self.calculate_average_features(results, results_mirrored)

            # 5) Get landmark colors
            landmark_colors = self.calculate_landmark_colors(landmarks['poses3d'], gait_event_dic, self.fps)

            # 4) Build up response to API call
            response = {}
            response['File name'] = self.file_name
            response['Task name'] = self.task_name
            response = response | avg_results
            response['signals'] = signals
            response['landMarks'] = landmarks['poses2d'].tolist()
            response['landMarks_3D'] = landmarks['poses3d'].tolist()
            response['gait_event_dic'] = {
                k: v.tolist()
                for k, v in gait_event_dic.items()
            }
            response['gait_event_dic_mirrored'] = {
                k: v.tolist()
                for k, v in gait_event_dic_mirrored.items()
            }
            response['landmark_colors'] = landmark_colors.tolist()
            response['turning_metadata'] = turning_metadata
            response['segment_metrics'] = analysis["segment_metrics"]
            response['gait_quality'] = analysis["quality"]
            # Cache the outputs downstream of MeTRAbs so users can adjust the
            # walking/turn boundaries without running 3D pose estimation again.
            # These arrays are analysis data, not a second landmark estimate.
            response['gait_analysis_cache'] = {
                'fps': float(self.fps),
                'start_time': float(self.start_time),
                'start_frame_idx': int(self.start_frame_idx),
                'poses3d': landmarks['poses3d'].tolist(),
                'poses3d_orientation': landmarks['poses3d_orientation'].tolist(),
                'poses3d_mirrored': landmarks_mirrored['poses3d'].tolist(),
                'phases': phases.tolist(),
                'strides': strides.tolist(),
                'phases_mirrored': phases_mirrored.tolist(),
                'strides_mirrored': strides_mirrored.tolist(),
            }
        except Exception as e:
            traceback.print_exc()
            return Response(f"Error with gait analysis: {str(e)}", status=500)
        finally:
            # 5) Clean up memory
            if hasattr(self, "video") and self.video is not None:
                self.video.release()

        return response

    def detect_turn(self, poses_3d, minimum_turn_degrees=75.0):
        """Estimate one dominant body turn from the 3D shoulder/hip orientation.

        MeTRAbs does not provide a turn label, so the yaw proxy is formed from
        directed right-to-left shoulder and hip axes.  Only this one-dimensional
        orientation trace is smoothed; the landmark coordinates used for gait
        features remain untouched.  Turn boundaries are the 5% and 95% crossings
        of the net orientation change, making the reported duration and angular
        speeds independent of the walking speed toward or away from the camera.
        """
        poses = np.asarray(poses_3d, dtype=float)
        empty = {
            "is_turning": False,
            "start_frame": None,
            "end_frame": None,
            "start_video_frame": None,
            "end_video_frame": None,
            "start_time_seconds": None,
            "end_time_seconds": None,
            "duration_seconds": None,
            "angle_degrees": None,
            "mean_angular_speed_degrees_per_second": None,
            "peak_angular_speed_degrees_per_second": None,
            "direction": None,
        }
        if poses.ndim != 3 or len(poses) < 5:
            return empty

        yaw = self._body_yaw(poses)
        if yaw is None:
            return empty

        plateau = max(2, min(len(yaw) // 5, int(round(float(self.fps) * 0.5))))
        start_yaw = float(np.median(yaw[:plateau]))
        end_yaw = float(np.median(yaw[-plateau:]))
        delta = end_yaw - start_yaw
        angle_degrees = float(np.degrees(delta))
        if abs(angle_degrees) < minimum_turn_degrees:
            return empty

        signed_progress = (yaw - start_yaw) * np.sign(delta)
        total = abs(delta)
        start_candidates = np.flatnonzero(signed_progress >= 0.05 * total)
        if not len(start_candidates):
            return empty
        start_frame = int(start_candidates[0])
        end_candidates = np.flatnonzero(
            (np.arange(len(yaw)) > start_frame) & (signed_progress >= 0.95 * total)
        )
        if not len(end_candidates):
            return empty
        return self.measure_turn_range(poses, start_frame, int(end_candidates[0]))

    def _body_yaw(self, poses_3d):
        """Return the smoothed body-orientation trace used for turn analysis."""
        poses = np.asarray(poses_3d, dtype=float)
        if poses.ndim != 3 or len(poses) < 5:
            return None
        indices = {name: int(np.where(self._metrabs_joint_order == name)[0][0])
                   for name in ("rsho", "lsho", "rhip", "lhip")}
        hip_axis = poses[:, indices["rhip"]] - poses[:, indices["lhip"]]
        shoulder_axis = poses[:, indices["rsho"]] - poses[:, indices["lsho"]]

        def normalize(vectors):
            lengths = np.linalg.norm(vectors, axis=1, keepdims=True)
            return vectors / np.where(lengths > 1e-9, lengths, np.nan)

        hip_axis, shoulder_axis = normalize(hip_axis), normalize(shoulder_axis)
        reverse_shoulder = np.nansum(hip_axis * shoulder_axis, axis=1) < 0
        shoulder_axis[reverse_shoulder] *= -1
        body_axis = normalize(hip_axis + shoulder_axis)
        yaw = np.unwrap(np.arctan2(body_axis[:, 2], body_axis[:, 0]))
        if not np.all(np.isfinite(yaw)):
            valid = np.isfinite(yaw)
            if valid.sum() < 5:
                return None
            yaw = np.interp(np.arange(len(yaw)), np.flatnonzero(valid), yaw[valid])

        desired_window = max(5, int(round(float(self.fps) * 0.25)))
        window = min(desired_window, len(yaw) if len(yaw) % 2 else len(yaw) - 1)
        if window >= 5:
            yaw = savgol_filter(yaw, window_length=window, polyorder=2, mode="interp")
        return yaw

    def measure_turn_range(self, poses_3d, start_frame, end_frame):
        """Measure a detected or manually selected turn interval."""
        yaw = self._body_yaw(poses_3d)
        if yaw is None:
            raise ValueError("Unable to calculate body orientation for this gait task.")
        start_frame = int(np.clip(start_frame, 0, len(yaw) - 2))
        end_frame = int(np.clip(end_frame, start_frame + 1, len(yaw) - 1))
        start_yaw = float(yaw[start_frame])
        end_yaw = float(yaw[end_frame])
        delta = end_yaw - start_yaw
        angle_degrees = float(np.degrees(delta))
        duration = (end_frame - start_frame) / float(self.fps)
        angular_velocity = np.gradient(yaw, 1.0 / float(self.fps))
        peak_speed = float(np.degrees(np.max(np.abs(angular_velocity[start_frame:end_frame + 1]))))
        return {
            "is_turning": True,
            "start_frame": start_frame,
            "end_frame": end_frame,
            "start_video_frame": int(self.start_frame_idx + start_frame),
            "end_video_frame": int(self.start_frame_idx + end_frame),
            "start_time_seconds": float(self.start_time + start_frame / self.fps),
            "end_time_seconds": float(self.start_time + end_frame / self.fps),
            "duration_seconds": float(duration),
            "angle_degrees": angle_degrees,
            "mean_angular_speed_degrees_per_second": float(abs(angle_degrees) / duration),
            "peak_angular_speed_degrees_per_second": peak_speed,
            "direction": "positive_yaw" if delta > 0 else "negative_yaw",
        }

    def analyze_straight_walking_segments(
        self,
        analyzer,
        phases,
        strides,
        poses,
        phases_mirrored,
        strides_mirrored,
        poses_mirrored,
        turning_metadata,
    ):
        """Analyze non-turning portions and pool their individual gait events."""
        frame_count = len(poses)
        if turning_metadata["is_turning"]:
            candidate_ranges = [
                (0, int(turning_metadata["start_frame"])),
                (int(turning_metadata["end_frame"]) + 1, frame_count),
            ]
        else:
            candidate_ranges = [(0, frame_count)]

        original_samples, mirrored_samples = [], []
        original_events = {key: [] for key in ("left_down", "left_up", "right_down", "right_up")}
        mirrored_events = {key: [] for key in original_events}
        segment_metrics, segment_quality = [], []

        for segment_index, (start, end) in enumerate(candidate_ranges, start=1):
            if end - start < max(5, int(round(self.fps))):
                segment_quality.append({
                    "segment": segment_index,
                    "start_frame": start,
                    "end_frame": max(start, end - 1),
                    "used": False,
                    "reason": "segment shorter than one second",
                })
                continue
            try:
                result, events, samples, quality = analyzer.analyze(
                    phases[start:end], strides[start:end], poses[start:end], self.fps,
                    return_details=True,
                )
                mirrored_result, mirrored_segment_events, mirrored_segment_samples, mirrored_quality = analyzer.analyze(
                    phases_mirrored[start:end], strides_mirrored[start:end],
                    poses_mirrored[start:end], self.fps, return_details=True,
                )
            except Exception as exc:
                segment_quality.append({
                    "segment": segment_index,
                    "start_frame": start,
                    "end_frame": end - 1,
                    "used": False,
                    "reason": str(exc),
                })
                continue

            original_samples.append(samples)
            mirrored_samples.append(mirrored_segment_samples)
            for key in original_events:
                original_events[key].extend((np.asarray(events[key]) + start).tolist())
                mirrored_events[key].extend((np.asarray(mirrored_segment_events[key]) + start).tolist())

            direction = self._walking_direction(poses[start:end])
            segment_metrics.append({
                "segment": segment_index,
                "direction_qc": direction,
                "start_frame": int(start),
                "end_frame": int(end - 1),
                "start_video_frame": int(self.start_frame_idx + start),
                "end_video_frame": int(self.start_frame_idx + end - 1),
                "step_count": int(len(events["left_down"]) + len(events["right_down"])),
                "features": self._json_numbers(result),
            })
            segment_quality.append({
                "segment": segment_index,
                "start_frame": start,
                "end_frame": end - 1,
                "used": True,
                "original": quality,
                "mirrored": mirrored_quality,
            })

        if not original_samples:
            raise ValueError("No straight-walking segment contained enough valid gait events.")

        return {
            "results": analyzer.pool_feature_samples(original_samples),
            "results_mirrored": analyzer.pool_feature_samples(mirrored_samples),
            "gait_event_dic": {key: np.asarray(value, dtype=float) for key, value in original_events.items()},
            "gait_event_dic_mirrored": {key: np.asarray(value, dtype=float) for key, value in mirrored_events.items()},
            "segment_metrics": segment_metrics,
            "quality": {
                "turn_excluded_from_primary_results": bool(turning_metadata["is_turning"]),
                "pooling_method": "all valid straight-walking events",
                "segments": segment_quality,
            },
        }

    def _walking_direction(self, poses):
        pelvis_index = int(np.where(self._metrabs_joint_order == "pelv")[0][0])
        depth = np.asarray(poses, dtype=float)[:, pelvis_index, 2]
        valid = np.isfinite(depth)
        if valid.sum() < 2:
            return "unknown"
        slope = np.polyfit(np.flatnonzero(valid), depth[valid], 1)[0]
        if abs(slope) < 1e-6:
            return "approximately_stationary_depth"
        return "toward_camera" if slope < 0 else "away_from_camera"

    @staticmethod
    def _json_numbers(values):
        return {key: float(value) if np.isfinite(value) else None for key, value in values.items()}

    

    def prepare_video_parameters(self, request):
        """
        Prepares video parameters from the HTTP request:
         - Parses JSON for bounding box and time codes.
         - Saves the uploaded video file.
         - Computes the expanded bounding box.
         - Determines FPS and start/end frame indices.
        Returns a dictionary of parameters. 
        MUST DEFINE ALL ABSTRACT PROPERTIES. 
        """
        # Check if video id, json_data, video folder and video metadata file all exist
        video_id = request.GET.get('id', None)
        if not video_id:
            raise Exception("Video project id not provided.")
        
        json_raw = request.POST.get('json_data')
        if not json_raw:
            raise Exception("Missing 'json_data' in POST data")
        
        try:
            json_data = json.loads(json_raw)
        except json.JSONDecodeError:
            raise Exception("Invalid JSON in 'json_data'")

        self._progress = getattr(request, "analysis_progress", self._progress)
        self._cancelled = getattr(request, "analysis_cancelled", self._cancelled)
        self._check_cancelled()
        
        folder_path = os.path.join(settings.MEDIA_ROOT, "video_uploads", video_id)
        if not os.path.isdir(folder_path):
            raise Exception("Video project folder does not exist.")

        metadata_path = os.path.join(folder_path, "metadata.json")
        if not os.path.exists(metadata_path):
            raise Exception("Metadata file for video does not exist.")
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            try:
                metadata = json.load(f)
            except json.JSONDecodeError:
                raise Exception(f"Metadata file '{metadata_path}' cannot be decoded.")

                    
        #Getting video attributes
        file_name = metadata["metadata"]["video_name"]
        file_path = os.path.join(settings.MEDIA_ROOT, "video_uploads", video_id, file_name)
        task_name = f"{json_data['task_name']}_{json_data['id']}"
        video = cv2.VideoCapture(file_path)
        video_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
        video_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = video.get(cv2.CAP_PROP_FPS)
        rotation = metadata["metadata"]["rotation"]
        start_time = json_data['start_time']
        end_time = json_data['end_time']
        start_frame_idx = math.floor(fps * start_time)
        end_frame_idx = math.ceil(fps * end_time)

        # The browser duration is not always exactly frame_count / FPS (in
        # particular after the upload has been converted to a CFR working
        # video).  A Full Video task must use the frames we can actually
        # decode and track; otherwise the final browser-derived indices have
        # no subject bounding boxes and gait aborts before landmark inference.
        if json_data.get('full_video'):
            decoded_frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
            if decoded_frame_count < 1:
                raise Exception("Unable to determine the number of frames in the video.")
            start_time = 0.0
            end_time = decoded_frame_count / fps
            start_frame_idx = 0
            # The video reader treats this index as inclusive.
            end_frame_idx = decoded_frame_count - 1
        original_bounding_box = json_data['boundingBox']
        subject_bounding_boxes = [box for box in json_data['subject_bounding_boxes'] if start_frame_idx <= box['frameNumber'] <= end_frame_idx]
        new_x = int(max(0, original_bounding_box['x'] - original_bounding_box['width'] * 0.125))
        new_y = int(max(0, original_bounding_box['y'] - original_bounding_box['height'] * 0.125))
        new_width = int(min(video_width - new_x, original_bounding_box['width'] * 1.25))
        new_height = int(min(video_height - new_y, original_bounding_box['height'] * 1.25))
        enlarged_bounding_box = {
            'x': new_x,
            'y': new_y,
            'width': new_width,
            'height': new_height
        }
        height_cm = int(json_data.get('height')) if json_data.get('height') else None


        # Getting camera properties
        field_of_view = int(json_data.get('field_of_view')) if json_data.get('field_of_view') else None
        sensor_height = int(json_data.get('sensor_height')) if json_data.get('sensor_height') else None
        sensor_width = int(json_data.get('sensor_width')) if json_data.get('sensor_width') else None
        focal_length = int(json_data.get('focal_length')) if json_data.get('focal_length') else None
        temp_intrinsic = json_data.get('intrinsic_matrix')
        intrinsic_matrix = None if temp_intrinsic is None or np.any(np.array(temp_intrinsic) == None) else temp_intrinsic
        temp_extrinsic = json_data.get('extrinsic_matrix')
        extrinsic_matrix = None if temp_extrinsic is None or np.any(np.array(temp_extrinsic) == None) else temp_extrinsic

        # focal length [pixels] = focal length [mm] / sensor pixel size [µm/pixels]

        if(sensor_height != None and sensor_width != None and focal_length != None and intrinsic_matrix == None):
            fx = focal_length / sensor_width * 1000
            cx = video_width / 2
            fy = focal_length / sensor_height * 1000
            cy = video_height / 2
            intrinsic_matrix = [
                [fx, 0,  cx],
                [0,  fy, cy],
                [0,  0,   0],
            ]


        if ( abs(len(subject_bounding_boxes) - (end_frame_idx - start_frame_idx + 1)) > 1 ):
            print("Number of frames", end_frame_idx - start_frame_idx)
            print("Len of subject bounding boxes", len(subject_bounding_boxes))
            raise Exception("Subject bounding boxes not found in all frames of the task. The chosen subject may not be correct.")

        if(height_cm == None):
            raise Exception("Invalid or missing height.")


        #Set all necessary class attributes
        self.file_name = file_name
        self.file_path = file_path
        self.task_name = task_name
        self.video = video
        self.fps = fps
        self.rotation = rotation
        self.start_time = start_time
        self.end_time = end_time
        self.start_frame_idx = start_frame_idx
        self.end_frame_idx = end_frame_idx
        self.original_bounding_box = original_bounding_box
        self.enlarged_bounding_box = enlarged_bounding_box
        self.subject_bounding_boxes = subject_bounding_boxes
        self.height_cm = height_cm

        self.field_of_view = field_of_view
        self.sensor_height = sensor_height
        self.sensor_width = sensor_width
        self.focal_length = focal_length
        self.intrinsic_matrix = intrinsic_matrix
        self.extrinsic_matrix = extrinsic_matrix
        
        return {
            "video": video,
            "file_name": file_name,
            "file_path": file_path,
            "original_bounding_box": original_bounding_box,
            "enlarged_bounding_box": enlarged_bounding_box,
            "start_time": start_time,
            "end_time": end_time,
            "start_frame_idx": start_frame_idx,
            "end_frame_idx": end_frame_idx,
            "focal_length": focal_length,
            "height_cm": height_cm,
        }



    def get_detector(self) -> object:
        """
        Getter for the detector used by the task.

        Returns an instance of the detector using the detectors classes
        """
        if GaitTask._metrabs_detector is None:
            print("Loading PyTorch MeTRAbs model")
            model_path = os.path.join(
                settings.BASE_DIR, 'app', 'analysis', 'models',
                'metrabs_eff2l_384px_800k_28ds_pytorch'
            )
            GaitTask._metrabs_detector = load_metrabs_model(model_path)
            print("PyTorch MeTRAbs model loaded")
        return GaitTask._metrabs_detector



    def get_signal_analyzer(self) -> object:
        """
        Getter for the signal analyzer used by the task

        Returns an instance of the signal analyze using the analyzer classes
        """
        # Import lazily so landmark inference does not initialize JAX.
        from app.analysis.signal_analyzers.gait_signal_analyzer import GaitSignalAnalyzer
        return GaitSignalAnalyzer()

    

    def calculate_signal(self, poses3D, height_mm, L=60) -> dict:
        """
        Processes 3D keypoints using the gait transformer model and returns phases, strides.

        Parameters:
            output_directory (str): Directory to save the resulting JSON file.
            height (float): Subject height in mm
            L (int): Window length for inference
            pos_divider (int): Positional divider used in model loading
        """

        pos_divider = max(1, round(self.fps / 30.0))
        if pos_divider not in GaitTask._gait_phase_transformers:
            GaitTask._gait_phase_transformers[pos_divider] = load_default_model(
                pos_divider=pos_divider
            )
        gait_phase_transformer = GaitTask._gait_phase_transformers[pos_divider]
        GaitTask._gait_phase_order_idx = np.array(
            [self._metrabs_joint_order.tolist().index(j) for j in GaitTask._gait_phase_joint_order]
        )

        keypoints = poses3D.copy()[:, GaitTask._gait_phase_order_idx]
        keypoints = keypoints / 1000.0
        keypoints = keypoints - np.mean(keypoints, axis=1, keepdims=True)
        keypoints = keypoints[:, :, [0, 2, 1]]
        keypoints[:, :, 2] *= -1


        # Run inference
        height_arr = np.array(height_mm, dtype=float)
        phases, strides = gait_phase_stride_inference(
            keypoints, height_arr, gait_phase_transformer, int(L * pos_divider)
        )
            
        signals = {}

        # Foot position
        signals["Foot right angle"] = list(strides[:, 0])
        signals["Foot left angle"] = list(strides[:, 1])

        # Foot velocity
        signals["Foot right velocity"] = list(strides[:, 3])
        signals["Foot left velocity"] = list(strides[:, 4])

        # Pelvis velocity
        signals["Pelvis velocity"] = list(strides[:, 2])

        # Hip angles
        signals["Hip right angle"] = list(strides[:, 5])
        signals["Hip left angle"] = list(strides[:, 6])

        # Knee angles
        signals["Knee right angle"] = list(strides[:, 7])
        signals["Knee left angle"] = list(strides[:, 8])

        # Phases
        signals["Phase 0"] = list(phases[:, 0])
        signals["Phase 1"] = list(phases[:, 1])
        signals["Phase 2"] = list(phases[:, 2])
        signals["Phase 3"] = list(phases[:, 3])

        signals = {key: [float(v) for v in value] for key, value in signals.items()}
        return phases, strides, signals




    def extract_landmarks(self, detector=None) -> tuple:
        """
        Process video frames between start_frame and end_frame and extract hand landmarks 
        for the left hand from each frame — both normal and horizontally mirrored versions.

        Returns:
            tuple: (all_preds, mirrored_all_preds)
                - all_preds: dict with keys "poses2d", "poses3d", "boxes" for the normal frames
                - mirrored_all_preds: dict with keys "poses2d", "poses3d", "boxes" for the mirrored frames
        """
        # Set up video and task arguments
        file_path = self.file_path
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        start_frame = self.start_frame_idx
        end_frame = self.end_frame_idx

        # Set up lists for extracting landmarks
        poses2d_lists, poses3d_lists, boxes_lists = [], [], []
        poses2d_lists_mirr, poses3d_lists_mirr, boxes_lists_mirr = [], [], []
        missing_mask = []
        multiple_people_detected = False

        cap = cv2.VideoCapture(file_path)
        cap.release()

        # Set up video reader
        # Eight frames keeps GPU utilization high while bounding cancellation
        # latency. Cancellation is also checked between normal and mirrored
        # passes, so a request never waits for an unnecessary second inference.
        batch_size = 8
        vid = self.video_reader(file_path, batch_size, start_frame, end_frame)
        raw_frame_idx = start_frame
        total_frames = max(1, end_frame - start_frame + 1)

        # Iterate over every frame batch
        for frame_batch in tqdm(vid, desc=f"Processing {file_name}"):
            self._check_cancelled()
            # --- Prepare tensors for BOTH original and mirrored batches ---
            batch_np = frame_batch
            device = GaitTask._metrabs_detector.device
            batch_tensor = torch.from_numpy(batch_np).permute(0, 3, 1, 2).to(device=device, dtype=torch.uint8)
            batch_tensor_mirr = torch.flip(batch_tensor, dims=[3])
            batch_size = batch_tensor.shape[0]
            frame_idx_list = list(range(raw_frame_idx, raw_frame_idx + batch_size))
            raw_frame_idx += batch_size

            # --- Create bounding boxes for original frames ---
            bbox_map = {
                item["frameNumber"]: item["data"][0]
                for item in self.subject_bounding_boxes
                if item.get("data")
            }
            rot_w = int(batch_np.shape[2])
            boxes_list = []
            mirrored_list = []
            for frame_num in frame_idx_list:
                subject_box = bbox_map.get(frame_num)
                if subject_box is None:
                    raise Exception(f"No bounding box for frame {frame_num}")

                x, y, w, h = (float(subject_box['x']),
                    float(subject_box['y']),
                    float(subject_box['width']),
                    float(subject_box['height']),
                )
                boxes_list.append([[x, y, w, h]])
                mirrored_x = rot_w - (x + w)
                mirrored_list.append([[mirrored_x, y, w, h]])

            boxes = torch.as_tensor(boxes_list, dtype=torch.float32, device=device)
            boxes_mirrored = torch.as_tensor(mirrored_list, dtype=torch.float32, device=device)

            # --- Set up optional camera parameters for this ---
            scalar_camera_args = {
                k: int(v) 
                for k, v in
                {
                    "default_fov_degrees": self.field_of_view,
                }.items()
                if v != None
            }
            matrix_camera_args = {
                k: torch.as_tensor(np.stack([v] * batch_size), dtype=torch.float32, device=device)
                for k, v in {
                    "intrinsic_matrix": self.intrinsic_matrix,
                    "extrinsic_matrix": self.extrinsic_matrix,
                }.items()
                if v is not None
            }
            print("matrix_camera_args",matrix_camera_args)

            with torch.inference_mode(), torch.device(device):
                pred = GaitTask._metrabs_detector.estimate_poses_batched(
                    images=batch_tensor,
                    boxes=boxes,
                    skeleton=self.skeleton,
                    **scalar_camera_args,
                    **matrix_camera_args,
                )
                self._check_cancelled()
                pred_mirr = GaitTask._metrabs_detector.estimate_poses_batched(
                    images=batch_tensor_mirr,
                    boxes=boxes_mirrored,
                    skeleton=self.skeleton,
                    **scalar_camera_args,
                    **matrix_camera_args,
                )

            # --- Accumulate both original and mirrored detections ---
            for j in range(batch_size):
                # ORIGINAL
                if pred["poses2d"][j].shape[0] > 0:
                    poses2d_lists.append(pred["poses2d"][j][0].detach().cpu().numpy())
                    poses3d_lists.append(pred["poses3d"][j][0].detach().cpu().numpy())
                    missing = False
                else:
                    # fill NaNs
                    poses2d_lists.append(np.full([17,2], np.nan, np.float32))
                    poses3d_lists.append(np.full([17,3], np.nan, np.float32))
                    missing = True
                missing_mask.append(missing)
                if pred["poses2d"][j].shape[0] > 1:
                    multiple_people_detected = True

                # MIRRORED
                if pred_mirr["poses2d"][j].shape[0] > 0:
                    poses2d_lists_mirr.append(pred_mirr["poses2d"][j][0].detach().cpu().numpy())
                    poses3d_lists_mirr.append(pred_mirr["poses3d"][j][0].detach().cpu().numpy())
                else:
                    poses2d_lists_mirr.append(np.full([17,2], np.nan, np.float32))
                    poses3d_lists_mirr.append(np.full([17,3], np.nan, np.float32))

            del pred, pred_mirr, batch_tensor, batch_tensor_mirr
            completed = min(total_frames, raw_frame_idx - start_frame)
            self._progress(
                5 + int(70 * completed / total_frames),
                f"Estimating 3D gait landmarks ({completed}/{total_frames} frames)…",
            )

        # --- Post‐processing for ORIGINAL ---
        all_poses2d = np.stack(poses2d_lists, axis=0)
        ox1 = self.original_bounding_box['x']
        oy1 = self.original_bounding_box['y']
        all_poses3d = np.stack(poses3d_lists, axis=0)
        missing_mask = np.array(missing_mask)
        interp2d = self.interpolate_missing_poses(all_poses2d, missing_mask)
        interp3d = self.interpolate_missing_poses(all_poses3d, missing_mask)
        corr3d   = self.correct_left_right_swapping(interp3d)
        all_preds = {
            "poses2d": interp2d,
            "poses3d": corr3d,
            "poses3d_orientation": interp3d,
        }

        # --- Post‐processing for MIRRORED (same pipeline) ---
        mir_poses2d = np.stack(poses2d_lists_mirr, axis=0)
        mir_poses3d = np.stack(poses3d_lists_mirr, axis=0)
        mir_interp2d = self.interpolate_missing_poses(mir_poses2d, missing_mask)
        mir_interp3d = self.interpolate_missing_poses(mir_poses3d, missing_mask)
        mir_corr3d   = self.correct_left_right_swapping(mir_interp3d)
        mirrored_all_preds = {
            "poses2d": mir_interp2d,
            "poses3d": mir_corr3d,
            "poses3d_orientation": mir_interp3d,
        }

        # --- warnings & return ---
        if multiple_people_detected:
            print(f"Warning: {file_name} had multiple people in some frames.")
        if missing_mask.sum() > 0:
            print(f"Warning: {missing_mask.sum()} frames found no person, saved under undetected dir.")
        print(f"Completed processing {file_name}")

        return all_preds, mirrored_all_preds



    def calculate_normalization_factor(self, essential_landmarks) -> float:
        """
        Return a caluclated scalar factor used to normalize the raw 1D signal.
        """
        return None
    


    def calculate_landmark_colors(self, poses_3D, gait_event_dic, fps=None):
        """
        Colour the left/right ankles green during stance and blue during swing.
        """

        def to_idx(arr):
            """Floor to int and keep inside [0, n_frames-1]."""
            return np.clip(np.floor(arr).astype(int), 0, n_frames - 1)

        def stance_mask(downs, ups):
            """Build stance Boolean mask with no ordering assumptions."""
            ev = [(int(t), 'd') for t in downs] + [(int(t), 'u') for t in ups]
            ev.sort(key=lambda x: x[0])

            mask = np.zeros(n_frames, dtype=bool)
            in_stance = bool(ev and ev[0][1] == 'u')
            last_t = 0
            for t, kind in ev:
                t = np.clip(t, 0, n_frames)
                if in_stance:
                    mask[last_t:t] = True
                in_stance = (kind == 'd')
                last_t = t
            if in_stance:
                mask[last_t:] = True
            return mask

        n_frames, n_joints = poses_3D.shape[:2]
        landmark_colors = np.full((n_frames, n_joints, 3), [255, 0, 0], dtype=np.uint8)

        # joint indices in your Metrabs order
        L_ANK = int(np.where(self._metrabs_joint_order == "lank")[0][0])
        R_ANK = int(np.where(self._metrabs_joint_order == "rank")[0][0])

        # convert lists → int frame indices
        ld = to_idx(gait_event_dic.get('left_down',  []))
        lu = to_idx(gait_event_dic.get('left_up',    []))
        rd = to_idx(gait_event_dic.get('right_down', []))
        ru = to_idx(gait_event_dic.get('right_up',   []))

        # stance masks
        left_stance  = stance_mask(ld, lu)
        right_stance = stance_mask(rd, ru)

        # colour ankles
        landmark_colors[left_stance,  L_ANK] = [0, 255,   0]   # stance green
        landmark_colors[~left_stance, L_ANK] = [0,   0, 255]   # swing blue
        landmark_colors[right_stance, R_ANK] = [0, 255,   0]
        landmark_colors[~right_stance, R_ANK] = [0,   0, 255]

        return landmark_colors
    # -------------------------------------------------------------
    # --- END: Abstract methods definitions
    # -------------------------------------------------------------





    # -------------------------------------------------------------
    # --- START: Custom helper methods definitions
    # -------------------------------------------------------------
    # ----- Function for calculating the averages features of original and mirrored videos
    def calculate_average_features(self, original_features, mirrored_features):
        average = {
            "Average stance time": (original_features["Average stance time"] + mirrored_features["Average stance time"]) / 2.0,
            "Average swing time": (original_features["Average swing time"] + mirrored_features["Average swing time"]) / 2.0,
            "Average double support time": (original_features["Average double support time"] + mirrored_features["Average double support time"]) / 2.0,
            "Average step time": (original_features["Average step time"] + mirrored_features["Average step time"]) / 2.0,
            "Average step length": (original_features["Average step length"] + mirrored_features["Average step length"]) / 2.0,
            "Average velocity": (original_features["Average velocity"] + mirrored_features["Average velocity"]) / 2.0,
            "Average cadence": (original_features["Average cadence"] + mirrored_features["Average cadence"]) / 2.0,
            "Average stance time left": (original_features["Average stance time left"] + mirrored_features["Average stance time right"]) / 2.0,
            "Average stance time right": (original_features["Average stance time right"] + mirrored_features["Average stance time left"]) / 2.0,
            "Average swing time left": (original_features["Average swing time left"] + mirrored_features["Average swing time right"]) / 2.0,
            "Average swing time right": (original_features["Average swing time right"] + mirrored_features["Average swing time left"]) / 2.0,
            "Average step time left": (original_features["Average step time left"] + mirrored_features["Average step time right"]) / 2.0,
            "Average step time right": (original_features["Average step time right"] + mirrored_features["Average step time left"]) / 2.0,
            "Average step length left": (original_features["Average step length left"] + mirrored_features["Average step length right"]) / 2.0,
            "Average step length right": (original_features["Average step length right"] + mirrored_features["Average step length left"]) / 2.0,
            "Arm swing correlation": (original_features["Arm swing correlation"] + mirrored_features["Arm swing correlation"]) / 2.0,
        }
        # A mirrored pass exchanges anatomical left/right. Preserve that
        # relationship while averaging the new wrist-amplitude measures.
        if "Arm swing left" in original_features and "Arm swing right" in mirrored_features:
            average["Arm swing left"] = (
                original_features["Arm swing left"] + mirrored_features["Arm swing right"]
            ) / 2.0
        if "Arm swing right" in original_features and "Arm swing left" in mirrored_features:
            average["Arm swing right"] = (
                original_features["Arm swing right"] + mirrored_features["Arm swing left"]
            ) / 2.0
        # SynthGait-compatible features are symmetric under the mirrored pass.
        # They are optional to preserve compatibility with older imported JSON.
        for name in (
            "SynthGait step length",
            "Step width",
            "Stooped posture",
            "Arm swing",
            "Step length variability",
            "Step width variability",
            "Step speed variability",
            "Torso medial-lateral displacement",
            "Torso medial-lateral displacement range",
            "Torso medial-lateral trunk motion ROM",
        ):
            if name in original_features and name in mirrored_features:
                average[name] = (original_features[name] + mirrored_features[name]) / 2.0
                
        return average
    
    ### ----- Function for interpolating missing poses -----
    def interpolate_missing_poses(self, poses: np.ndarray, missing_mask: np.ndarray) -> np.ndarray:
        """
        Fill missing frames in `poses` by linear interpolation between the closest
        non-missing frames on each side.  If only one neighbor exists, does a constant
        fill.  Raises if all frames are missing or if any missing frame has no neighbors.
        
        Args:
            poses        (T, J, D) array of keypoints with NaNs for missing frames
            missing_mask (T,)  boolean array, True where frame is entirely missing
        
        Returns:
            poses_interp (T, J, D) array with missing frames filled
        """
        poses_interp = poses.copy()
        T, J, D = poses.shape
        missing_mask = missing_mask.astype(bool)
        
        # At least one frame must be valid
        if missing_mask.all():
            raise ValueError("Cannot interpolate when all frames are missing.")
        
        # Compute nearest valid index on the left for each t
        idx = np.arange(T)
        left_valid = np.where(~missing_mask, idx, -1)
        left_neighbors = np.maximum.accumulate(left_valid)
        
        # Compute nearest valid index on the right for each t
        rev_idx = idx[::-1]
        right_valid_rev = np.where(~missing_mask[::-1], rev_idx, T)
        right_neighbors_rev = np.minimum.accumulate(right_valid_rev)
        right_neighbors = right_neighbors_rev[::-1]
        
        # Indices of frames to fill
        miss_idx = np.nonzero(missing_mask)[0]
        
        # Check every missing frame has at least one neighbor
        no_left  = left_neighbors[miss_idx]  == -1
        no_right = right_neighbors[miss_idx] == T
        if np.any(no_left & no_right):
            bad = miss_idx[no_left & no_right]
            raise ValueError(f"Frame(s) {bad.tolist()} have no neighbors with real values.")
        
        # 1) Frames with both neighbors → linear interp
        both = ~(no_left | no_right)
        mi_both  = miss_idx[both]
        li, ri  = left_neighbors[mi_both], right_neighbors[mi_both]
        dt = (ri - li).astype(float)
        w_right = (mi_both - li) / dt    # weight for the 'right' point
        w_left  = (ri - mi_both) / dt    # weight for the 'left'  point
        
        P_left  = poses[li]              # (N, J, D)
        P_right = poses[ri]              # (N, J, D)
        interp  = (P_left * w_left[:,None,None]
                + P_right * w_right[:,None,None])
        poses_interp[mi_both] = interp
        
        # 2) Frames with only left neighbor → constant fill
        left_only_idx = miss_idx[no_right & ~no_left]
        poses_interp[left_only_idx] = poses[left_neighbors[left_only_idx]]
        
        # 3) Frames with only right neighbor → constant fill
        right_only_idx = miss_idx[no_left & ~no_right]
        poses_interp[right_only_idx] = poses[right_neighbors[right_only_idx]]
        
        return poses_interp
    


    def correct_left_right_swapping(self, poses, window_size=3, margin=100):
        """
        For each frame f, directly compare that frame's left/right
        joint positions to each of the previous `window_size` frames.
        If a majority say 'swap is more consistent', then swap at f.
        Margin is 100mm
        """
        metrabs_joint_order = np.array([
            'htop','neck','rsho','relb','rwri','lsho','lelb','lwri',
            'rhip','rkne','rank','lhip','lkne','lank','pelv','spin','head'
        ])
        IDX = {name: i for i, name in enumerate(metrabs_joint_order)}
        PAIRS = [
            ('lwri','rwri'),
            ('lelb','relb'),
            ('lsho','rsho'),
            ('lank','rank'),
            ('lkne','rkne'),
            ('lhip','rhip'),
        ]

        F, J, _ = poses.shape
        fixed_poses = poses.copy()
        swapped = False

        for f in range(1, F):
            start = max(0, f - window_size)
            prev_idxs = range(start, f)
            for left_name, right_name in PAIRS:
                Li, Ri = IDX[left_name], IDX[right_name]
                curL, curR = fixed_poses[f, Li], fixed_poses[f, Ri]

                swap_votes = 0
                for p in prev_idxs:
                    prevL, prevR = fixed_poses[p, Li], fixed_poses[p, Ri]
                    dd_same = np.linalg.norm(curL - prevL) + np.linalg.norm(curR - prevR)
                    dd_swap = np.linalg.norm(curL - prevR) + np.linalg.norm(curR - prevL)

                    if dd_swap + margin < dd_same:
                        swap_votes += 1

                if swap_votes > len(prev_idxs) / 2.0:
                    swapped = True
                    fixed_poses[f, [Li, Ri]] = fixed_poses[f, [Ri, Li]]
        if swapped: print("Warning: Swap was performed on frames")
        return fixed_poses
    


    # Video Reader helper function
    def video_reader(self, filepath, batch_size=4, start_frame=0, end_frame=None):
        if not os.path.isfile(filepath):
            print("Error: File path is not a video")
            return None, None
        
        cap = cv2.VideoCapture(filepath)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        frames = []
        frame_idx = start_frame

        while True:
            ret, frame_bgr = cap.read()
            if not ret:
                if frames:
                    yield np.stack(frames)
                break

            if end_frame is not None and frame_idx > end_frame:
                if frames:
                    yield np.stack(frames)
                break

            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            rotation_code = {
                90: cv2.ROTATE_90_CLOCKWISE,
                180: cv2.ROTATE_180,
                270: cv2.ROTATE_90_COUNTERCLOCKWISE
            }.get(self.rotation, None)
            if rotation_code is not None:
                frame_rgb = cv2.rotate(frame_rgb, rotation_code)
            frames.append(frame_rgb)
            frame_idx += 1

            if len(frames) == batch_size:
                yield np.stack(frames)
                frames = []
        cap.release()

        
    # -------------------------------------------------------------
    # --- END: Custom helper methods definitions
    # -------------------------------------------------------------
