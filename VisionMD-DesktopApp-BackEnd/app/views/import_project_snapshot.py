"""Import a complete VisionMD project snapshot into an existing video project."""

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response


def _snapshot_data(payload):
    """Accept the new snapshot envelope and the former screen-level exports."""
    if not isinstance(payload, dict):
        raise ValueError("The JSON document must be an object.")

    if payload.get("format") == "visionmd-project":
        if payload.get("version") != 1:
            raise ValueError("This VisionMD project snapshot version is not supported.")
        payload = payload.get("data")
        if not isinstance(payload, dict):
            raise ValueError("Project snapshot data is missing.")

    result = {}
    for name in ("persons", "boundingBoxes", "tasks"):
        value = payload.get(name)
        if value is not None:
            if not isinstance(value, list):
                raise ValueError(f"{name} must be an array.")
            result[name] = value

    if not result:
        raise ValueError("No VisionMD project data was found in this JSON file.")
    return result


def _positive_number(value, label, integer=False):
    try:
        number = int(value) if integer else float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{label} must be a positive number.") from None
    if number <= 0 or (not integer and not math.isfinite(number)):
        raise ValueError(f"{label} must be a positive number.")
    return number


def _bounding_box_frame_count(slices):
    boxes = slices.get("boundingBoxes")
    if not boxes:
        return None
    frame_numbers = []
    for entry in boxes:
        if not isinstance(entry, dict):
            raise ValueError("Each boundingBoxes entry must be an object.")
        try:
            frame = int(entry["frameNumber"])
        except (KeyError, TypeError, ValueError, OverflowError):
            raise ValueError("Each boundingBoxes entry must have a non-negative frameNumber.") from None
        if frame < 0:
            raise ValueError("Each boundingBoxes entry must have a non-negative frameNumber.")
        frame_numbers.append(frame)
    return max(frame_numbers) + 1


def _validate_snapshot_identity(payload, slices, metadata):
    """Reject a snapshot produced for a different video or frame timeline."""
    if payload.get("format") != "visionmd-project":
        # Older screen-level exports contain no video identity. Keep accepting
        # them, but do not pretend that they can be verified.
        return

    video = payload.get("video")
    if not isinstance(video, dict):
        raise ValueError("Project snapshot video metadata is missing.")

    snapshot_name = video.get("name")
    current_name = metadata.get("video_name")
    if not snapshot_name or not current_name:
        raise ValueError("Project snapshot or uploaded video name is missing.")
    # Upload normalization may change MOV to MP4, so compare the stable stem.
    if Path(str(snapshot_name)).stem.casefold() != Path(str(current_name)).stem.casefold():
        raise ValueError(
            f"Project JSON is for '{snapshot_name}', but this video is '{current_name}'."
        )

    snapshot_fps = video.get("fps")
    current_fps = metadata.get("fps")
    if snapshot_fps is not None and current_fps is not None:
        snapshot_fps = _positive_number(snapshot_fps, "Project snapshot FPS")
        current_fps = _positive_number(current_fps, "Uploaded video FPS")
        tolerance = max(0.05, current_fps * 0.002)
        if abs(snapshot_fps - current_fps) > tolerance:
            raise ValueError(
                f"Project JSON FPS ({snapshot_fps:.6g}) does not match "
                f"the uploaded video ({current_fps:.6g})."
            )

    declared_count = video.get("frame_count")
    if declared_count is not None:
        declared_count = _positive_number(
            declared_count, "Project snapshot frame_count", integer=True
        )
    box_count = _bounding_box_frame_count(slices)
    if declared_count is not None and box_count is not None and declared_count != box_count:
        raise ValueError(
            f"Project JSON is internally inconsistent: video.frame_count is "
            f"{declared_count}, but boundingBoxes cover {box_count} frames."
        )
    snapshot_count = declared_count if declared_count is not None else box_count
    current_count = metadata.get("frame_count")
    if current_count is not None:
        current_count = _positive_number(
            current_count, "Uploaded video frame_count", integer=True
        )
        if snapshot_count is None:
            raise ValueError(
                "Project JSON has no verifiable frame count. Regenerate it with "
                "the current VisionMD batch exporter."
            )
        if snapshot_count != current_count:
            raise ValueError(
                f"Project JSON contains {snapshot_count} frames, but the uploaded "
                f"video contains {current_count}. The analysis cannot be aligned safely."
            )


@api_view(["POST"])
def import_project_snapshot(request):
    video_id = request.GET.get("id")
    if not video_id:
        return Response("Video project id not provided.", status=400)

    project_path = os.path.join(settings.MEDIA_ROOT, "video_uploads", video_id)
    if not os.path.isdir(project_path):
        return Response("Video project does not exist.", status=404)

    try:
        slices = _snapshot_data(request.data)
        metadata_path = os.path.join(project_path, "metadata.json")
        with open(metadata_path, "r", encoding="utf-8") as handle:
            metadata_wrapped = json.load(handle)
        metadata = metadata_wrapped.get("metadata")
        if not isinstance(metadata, dict):
            raise ValueError("Uploaded video metadata is missing.")

        # Validate everything before writing any slice, so a rejected import
        # cannot partially replace an existing project.
        _validate_snapshot_identity(request.data, slices, metadata)

        for name, data in slices.items():
            with open(os.path.join(project_path, f"{name}.json"), "w", encoding="utf-8") as handle:
                json.dump({name: data}, handle, indent=4)

        metadata["last_edited"] = datetime.now(timezone.utc).isoformat()
        with open(metadata_path, "w", encoding="utf-8") as handle:
            json.dump(metadata_wrapped, handle, indent=4)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return Response(f"Invalid project snapshot: {exc}", status=400)

    return Response({"imported": sorted(slices)}, status=200)
