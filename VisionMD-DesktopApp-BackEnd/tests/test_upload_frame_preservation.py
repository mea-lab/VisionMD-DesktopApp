"""Frame-preserving upload regression tests; no model inference is needed."""
import json
import os
from pathlib import Path
import subprocess

import pytest
from django.test import override_settings
from rest_framework.test import APIRequestFactory

from app.views.upload_video import (
    convert_to_mp4, get_ffmpeg_path, get_ffprobe_path, probe_decoded_video_timing,
    probe_first_video_timestamp, upload_video,
)


def check_upload(source, media_root):
    before_count, before_duration = probe_decoded_video_timing(str(source))
    with override_settings(MEDIA_ROOT=str(media_root)):
        with source.open("rb") as stream:
            request = APIRequestFactory().post("/", {"video": stream}, format="multipart")
            response = upload_video(request)
    assert response.status_code == 200, response.data
    metadata = response.data["metadata"]
    output = media_root / "video_uploads" / metadata["id"] / metadata["video_name"]
    count, duration = probe_decoded_video_timing(str(output))
    assert count == before_count == metadata["frame_count"] == metadata["source_frame_count"]
    assert abs(duration - before_duration) < 1 / metadata["fps"]
    frames = json.loads(subprocess.check_output([
        get_ffprobe_path(), "-v", "error", "-select_streams", "v:0", "-show_frames",
        "-show_entries", "frame=best_effort_timestamp_time", "-of", "json", str(output),
    ]))["frames"]
    timestamps = [float(frame["best_effort_timestamp_time"]) for frame in frames]
    step = 1 / metadata["fps"]
    assert abs(timestamps[0]) <= .001
    assert all(abs((b - a) - step) < .001 for a, b in zip(timestamps, timestamps[1:]))


def test_cfr_with_positive_start_is_rebased(tmp_path):
    source = tmp_path / "offset.mp4"
    subprocess.run([
        get_ffmpeg_path(), "-v", "error", "-y", "-f", "lavfi",
        "-i", "testsrc2=size=160x120:rate=30", "-frames:v", "90",
        "-vf", "setpts=PTS+0.2/TB", "-fps_mode", "passthrough",
        "-c:v", "libx264", str(source),
    ], check=True)
    assert probe_first_video_timestamp(str(source)) == pytest.approx(0.2, abs=.001)
    check_upload(source, tmp_path / "media")


def test_irregular_timestamps_preserve_frames(tmp_path):
    source = tmp_path / "irregular.mov"
    subprocess.run([
        get_ffmpeg_path(), "-v", "error", "-y", "-f", "lavfi",
        "-i", "testsrc2=size=160x120:rate=30", "-frames:v", "211",
        "-vf", "setpts=PTS+0.2/TB*gte(N\\,60)",
        "-fps_mode", "passthrough", "-c:v", "libx264", str(source),
    ], check=True)
    check_upload(source, tmp_path / "media")


def test_mp4_container_conversion_does_not_reencode_video(tmp_path):
    source = tmp_path / "source.mov"
    subprocess.run([
        get_ffmpeg_path(), "-v", "error", "-y", "-f", "lavfi",
        "-i", "testsrc2=size=160x120:rate=30", "-f", "lavfi",
        "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-frames:v", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(source),
    ], check=True)

    before_hash = subprocess.check_output([
        get_ffmpeg_path(), "-v", "error", "-i", str(source),
        "-map", "0:v:0", "-f", "framemd5", "-",
    ])
    output = convert_to_mp4(str(source))
    after_hash = subprocess.check_output([
        get_ffmpeg_path(), "-v", "error", "-i", output,
        "-map", "0:v:0", "-f", "framemd5", "-",
    ])

    assert before_hash == after_hash
    assert not source.exists()


@pytest.mark.skipif(not os.environ.get("VISIONMD_UPLOAD_REGRESSION_VIDEO"),
                    reason="Optional real recording supplied by environment")
def test_original_recording(tmp_path):
    check_upload(Path(os.environ["VISIONMD_UPLOAD_REGRESSION_VIDEO"]), tmp_path / "media")
