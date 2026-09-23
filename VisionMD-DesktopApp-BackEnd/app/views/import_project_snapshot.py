"""Import a complete VisionMD project snapshot into an existing video project."""

import json
import os
from datetime import datetime, timezone

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
        for name, data in slices.items():
            with open(os.path.join(project_path, f"{name}.json"), "w", encoding="utf-8") as handle:
                json.dump({name: data}, handle, indent=4)

        metadata_path = os.path.join(project_path, "metadata.json")
        with open(metadata_path, "r", encoding="utf-8") as handle:
            metadata_wrapped = json.load(handle)
        metadata_wrapped["metadata"]["last_edited"] = datetime.now(timezone.utc).isoformat()
        with open(metadata_path, "w", encoding="utf-8") as handle:
            json.dump(metadata_wrapped, handle, indent=4)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return Response(f"Invalid project snapshot: {exc}", status=400)

    return Response({"imported": sorted(slices)}, status=200)
