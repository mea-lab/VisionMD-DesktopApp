"""Disk-backed cache for deterministic VisionMD task results."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from django.conf import settings

CACHE_VERSION = "visionmd-analysis-cache-v1"


def _project(video_id: str) -> Path:
    return Path(settings.MEDIA_ROOT) / "video_uploads" / str(video_id)


def cache_key(video_id: str, task_name: str, json_data: str) -> str:
    project = _project(video_id)
    metadata_path = project / "metadata.json"
    video_fingerprint = None
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))["metadata"]
        video = project / metadata["video_name"]
        stat = video.stat()
        video_fingerprint = [video.name, stat.st_size, stat.st_mtime_ns]
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        video_fingerprint = [str(metadata_path), metadata_path.stat().st_mtime_ns if metadata_path.exists() else None]
    try:
        parameters = json.loads(json_data)
    except (TypeError, json.JSONDecodeError):
        parameters = json_data
    payload = {"version":CACHE_VERSION,"video":video_fingerprint,
               "task":task_name,"parameters":parameters}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_cached(video_id: str, key: str):
    path = _project(video_id) / ".analysis_cache" / f"{key}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_cached(video_id: str, key: str, result: dict) -> None:
    directory = _project(video_id) / ".analysis_cache"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{key}.json"
    temporary = directory / f".{key}.{os.getpid()}.tmp"
    temporary.write_text(json.dumps(result, allow_nan=False, separators=(",", ":")), encoding="utf-8")
    os.replace(temporary, target)
