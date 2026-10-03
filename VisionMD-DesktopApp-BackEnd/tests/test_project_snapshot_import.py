"""Project snapshot identity checks requiring no model inference."""

import json

import pytest
from django.test import override_settings
from rest_framework.test import APIRequestFactory

from app.views.import_project_snapshot import import_project_snapshot


VIDEO_ID = "00000000"
FRAME_COUNT = 205
FPS = 205 / 6.838


def make_project(media_root):
    project = media_root / "video_uploads" / VIDEO_ID
    project.mkdir(parents=True)
    metadata = {
        "metadata": {
            "id": VIDEO_ID,
            "video_name": "001-045_Visit6_FT_R_good.mp4",
            "fps": FPS,
            "frame_count": FRAME_COUNT,
        }
    }
    (project / "metadata.json").write_text(json.dumps(metadata))
    (project / "tasks.json").write_text(json.dumps({"tasks": [{"id": "original"}]}))
    return project


def snapshot(frame_count=FRAME_COUNT, name="001-045_Visit6_FT_R_good.MOV",
             fps=FPS, declare_count=True):
    video = {"name": name, "fps": fps}
    if declare_count:
        video["frame_count"] = frame_count
    return {
        "format": "visionmd-project",
        "version": 1,
        "video": video,
        "data": {
            "persons": [],
            "boundingBoxes": [
                {"frameNumber": frame, "data": []}
                for frame in range(frame_count)
            ],
            "tasks": [{"id": 1}],
        },
    }


def send(payload, media_root):
    request = APIRequestFactory().post(
        f"/?id={VIDEO_ID}", payload, format="json"
    )
    with override_settings(MEDIA_ROOT=str(media_root)):
        return import_project_snapshot(request)


def test_matching_snapshot_imports_before_writing(tmp_path):
    project = make_project(tmp_path)
    response = send(snapshot(), tmp_path)
    assert response.status_code == 200
    assert json.loads((project / "tasks.json").read_text())["tasks"] == [{"id": 1}]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (snapshot(name="001-045_Visit1_FT_R_good.MOV"), "Project JSON is for"),
        (snapshot(frame_count=194), "194 frames"),
        (snapshot(fps=25), "FPS"),
        (snapshot(frame_count=194, declare_count=False), "194 frames"),
    ],
)
def test_mismatch_is_rejected_without_overwriting_project(tmp_path, payload, message):
    project = make_project(tmp_path)
    response = send(payload, tmp_path)
    assert response.status_code == 400
    assert message in str(response.data)
    assert json.loads((project / "tasks.json").read_text())["tasks"] == [
        {"id": "original"}
    ]


def test_enveloped_snapshot_requires_video_identity(tmp_path):
    project = make_project(tmp_path)
    payload = snapshot()
    del payload["video"]
    response = send(payload, tmp_path)
    assert response.status_code == 400
    assert "video metadata is missing" in str(response.data)
    assert json.loads((project / "tasks.json").read_text())["tasks"] == [
        {"id": "original"}
    ]
