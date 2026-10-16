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


def check_upload(source, media_root, preserve_original=False):
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
    if preserve_original:
        assert output.read_bytes() == source.read_bytes()
    else:
        assert abs(timestamps[0]) <= .001
    assert all(abs((b - a) - step) < .001 for a, b in zip(timestamps, timestamps[1:]))


def test_cfr_with_positive_start_is_preserved(tmp_path):
    source = tmp_path / "offset.mp4"
    subprocess.run([
        get_ffmpeg_path(), "-v", "error", "-y", "-f", "lavfi",
        "-i", "testsrc2=size=160x120:rate=30", "-frames:v", "90",
        "-vf", "setpts=PTS+0.2/TB", "-fps_mode", "passthrough",
        "-c:v", "libx264", str(source),
    ], check=True)
    assert probe_first_video_timestamp(str(source)) == pytest.approx(0.2, abs=.001)
    check_upload(source, tmp_path / "media", preserve_original=True)


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


def test_progress_endpoint_reports_current_stage():
    from django.core.cache import cache
    from app.views.upload_video import upload_progress
    cache.set('video-upload:regression', {'message': 'Verifying converted frame count and duration…'}, 60)
    try:
        request = APIRequestFactory().get('/', {'upload_id': 'regression'})
        response = upload_progress(request)
        assert response.status_code == 200
        assert response.data['message'].startswith('Verifying')
        request = APIRequestFactory().get('/', {'upload_id': 'missing-regression'})
        assert upload_progress(request).data['message'].startswith('Transferring')
    finally:
        cache.delete('video-upload:regression')


@pytest.mark.parametrize('angle', [90, 180, 270])
def test_preserved_cfr_upload_does_not_rotate_twice(tmp_path, angle):
    import cv2
    import numpy as np
    plain = tmp_path / 'plain.mp4'
    source = tmp_path / 'rotated.mov'
    subprocess.run([get_ffmpeg_path(), '-v', 'error', '-y', '-f', 'lavfi',
                    '-i', 'testsrc2=size=160x120:rate=30', '-frames:v', '30',
                    '-c:v', 'libx264', str(plain)], check=True)
    subprocess.run([get_ffmpeg_path(), '-v', 'error', '-y', '-i', str(plain),
                    '-c', 'copy', '-metadata:s:v:0', f'rotate={angle}', str(source)], check=True)
    cap = cv2.VideoCapture(str(source))
    ok, expected = cap.read()
    assert ok
    assert cap.get(cv2.CAP_PROP_ORIENTATION_AUTO)
    cap.release()
    media_root = tmp_path / 'media'
    with override_settings(MEDIA_ROOT=str(media_root)):
        with source.open('rb') as stream:
            response = upload_video(APIRequestFactory().post('/', {'video': stream}, format='multipart'))
    assert response.status_code == 200, response.data
    metadata = response.data['metadata']
    folder = media_root / 'video_uploads' / metadata['id']
    assert (folder / metadata['video_name']).read_bytes() == source.read_bytes()
    assert metadata['rotation'] == 0
    thumbnail = cv2.imread(str(folder / 'thumbnail.jpg'))
    assert thumbnail.shape == expected.shape
    # Compare to the exact JPEG encoding used by the upload, including pixels.
    ok, encoded = cv2.imencode('.jpg', expected)
    assert ok
    assert np.array_equal(thumbnail, cv2.imdecode(encoded, cv2.IMREAD_COLOR))


def test_subject_detection_uses_effective_upload_rotation(tmp_path, monkeypatch):
    import sys
    from types import ModuleType
    from app.views.get_bounding_boxes import get_bounding_boxes
    folder = tmp_path / 'video_uploads' / '00000000'
    folder.mkdir(parents=True)
    (folder / 'video.mov').touch()
    (folder / 'metadata.json').write_text(json.dumps({'metadata': {'video_name': 'video.mov', 'rotation': 0}}))
    calls = []
    detector = ModuleType('app.analysis.detectors.yolo_detectors')
    def tracker(path, rotation, model, device):
        calls.append(rotation)
        return {'boundingBoxes': []}
    detector.yolo_tracker = tracker
    monkeypatch.setitem(sys.modules, detector.__name__, detector)
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        response = get_bounding_boxes(APIRequestFactory().get('/', {'id': '00000000'}))
    assert response.status_code == 200
    assert calls == [0]
