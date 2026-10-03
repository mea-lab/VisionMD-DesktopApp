# detectors/yolo_detectors.py

import os
import cv2
import numpy as np
from .subject_candidates import rank_subject_candidates
from ultralytics import YOLO
from app.analysis.model_registry import get_model, reset_yolo_runtime
from app.analysis.torch_device import preferred_device, run_with_device_fallback

def create_yolo_detector(model_path="yolov8s.pt", device='auto'):
    """
    Example function that creates a YOLO object 
    """
    selected = preferred_device(device)
    return get_model(("yolo", os.path.abspath(model_path)), lambda: YOLO(model_path)), selected


def yolo_tracker(file_path, rotation, model_path="yolov8s.pt", device='auto'):
    """
    Runs YOLOv8 tracking and returns bounding boxes (every 10 frames),
    remapping IDs to be consecutive.
    """
    device = preferred_device(device)

    # Load YOLO model
    model = get_model(("yolo", os.path.abspath(model_path)), lambda: YOLO(model_path))
    reset_yolo_runtime(model)

    cap = cv2.VideoCapture(file_path)
    boundingBoxes = []
    frameNumber = 0
    data = []  # store the last set of detections between frames

    # Dictionary to remap original YOLO IDs to consecutive ones
    id_map = {}
    next_id = 1
    observations = {}
    sample_count = 0
    frame_area = 1

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        if rotation != 0:
            if rotation == 90:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            elif rotation == 180:
                frame = cv2.rotate(frame, cv2.ROTATE_180)
            elif rotation == 270:
                frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            else:
                raise ValueError("Rotation must be one of [0, 90, 180, 270]")

        if frameNumber % 10 == 0:
            sample_count += 1
            frame_area = frame.shape[0] * frame.shape[1]
            # Run YOLOv8 tracking on this frame
            def track(active_device):
                return model.track(
                    frame,
                    persist=True,
                    classes=[0],  # class 0 = person
                    verbose=False,
                    device=active_device,
                )

            results, device = run_with_device_fallback(
                track,
                device,
                label="YOLO person tracking",
                on_cpu_fallback=lambda: reset_yolo_runtime(model),
            )
            data = []

            if (len(results) > 0 and
                results[0].boxes is not None and
                results[0].boxes.id is not None):
                yolo_ids = results[0].boxes.id.cpu().numpy().astype(int)
                boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                confidences = results[0].boxes.conf.cpu().numpy()
                keypoints = results[0].keypoints
                pose_conf = keypoints.conf.cpu().numpy() if keypoints is not None and keypoints.conf is not None else None

                for i in range(len(yolo_ids)):
                    original_id = int(yolo_ids[i])

                    # Remap to consecutive ID
                    if original_id not in id_map:
                        id_map[original_id] = next_id
                        next_id += 1

                    mapped_id = id_map[original_id]

                    observations.setdefault(mapped_id, []).append({
                        "area": max(0, int(boxes[i][2]-boxes[i][0])) * max(0, int(boxes[i][3]-boxes[i][1])),
                        "confidence": float(confidences[i]),
                        "pose_quality": float(np.mean(pose_conf[i])) if pose_conf is not None else 0.,
                    })
                    temp = {
                        'id': mapped_id,
                        'x': int(boxes[i][0]),
                        'y': int(boxes[i][1]),
                        'width': int(boxes[i][2] - boxes[i][0]),
                        'height': int(boxes[i][3] - boxes[i][1]),
                        'Subject': False
                    }
                    data.append(temp)

            frameResults = {
                'frameNumber': frameNumber,
                'data': data
            }
            boundingBoxes.append(frameResults)
        else:
            # Repeat last known data
            frameResults = {
                'frameNumber': frameNumber,
                'data': data
            }
            boundingBoxes.append(frameResults)

        frameNumber += 1

    cap.release()
    candidates = rank_subject_candidates(observations, sample_count, frame_area)
    suggested_id = candidates[0]["id"] if candidates else None
    boundingBoxes = [{**frame, "data": [{**box, "Subject": box["id"] == suggested_id}
                      for box in frame["data"]]} for frame in boundingBoxes]
    return {"boundingBoxes": boundingBoxes, "candidates": candidates,
            "suggestedSubjectId": suggested_id}
