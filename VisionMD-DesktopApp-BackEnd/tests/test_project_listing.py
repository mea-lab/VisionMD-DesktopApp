import json
from pathlib import Path

from django.test import override_settings
from rest_framework.test import APIRequestFactory
import cv2

from app.views.get_video_metadata import get_video_metadata


def create_project(root, id, edited='2026-10-02T12:00:00Z'):
    folder = root / 'video_uploads' / id
    folder.mkdir(parents=True)
    metadata = dict(id=id, video_name='video.mp4', stem_name='video', file_type='mp4',
                    fps=30, thumbnail_url=f'/media/{id}/thumbnail.jpg',
                    video_url=f'/media/{id}/video.mp4', rotation=0, last_edited=edited)
    (folder / 'metadata.json').write_text(json.dumps({'metadata': metadata}))
    # Listing must not attempt to decode either these bytes or analysis JSON.
    (folder / 'video.mp4').write_bytes(b'Video deliberately not decoded by the listing')
    (folder / 'thumbnail.jpg').write_bytes(b'Saved thumbnail')
    (folder / 'tasks.json').write_text('{not valid json')
    return folder


def request(root, query=''):
    with override_settings(MEDIA_ROOT=str(root)):
        return get_video_metadata(APIRequestFactory().get('/'+query))


def test_listing_reads_each_metadata_once_without_video_or_snapshot_decoding(tmp_path, monkeypatch):
    older = create_project(tmp_path, '00000001')
    newer = create_project(tmp_path, '00000002', '2026-10-02T13:00:00Z')
    monkeypatch.setattr(cv2, 'VideoCapture', lambda *_: (_ for _ in ()).throw(AssertionError('Video decoded during listing')))
    opened = []
    original = Path.open
    def tracked(path, *args, **kwargs):
        opened.append(path)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', tracked)
    response = request(tmp_path)
    assert response.status_code == 200
    assert [d['metadata']['id'] for d in response.data] == ['00000002', '00000001']
    assert sorted(opened) == sorted([older/'metadata.json', newer/'metadata.json'])
    response = request(tmp_path, '?id=00000001')
    assert response.status_code == 200 and response.data['metadata']['id'] == '00000001'


def test_unreadable_and_incomplete_projects_are_skipped_without_deletion(tmp_path):
    valid = create_project(tmp_path, '00000001')
    broken = create_project(tmp_path, '00000002')
    (broken/'metadata.json').write_text('{invalid')
    missing = create_project(tmp_path, '00000003')
    (missing/'thumbnail.jpg').unlink()
    empty = tmp_path/'video_uploads'/'00000004';empty.mkdir()
    response = request(tmp_path)
    assert [d['metadata']['id'] for d in response.data] == ['00000001']
    assert all(p.is_dir() for p in [valid, broken, missing, empty])
    assert request(tmp_path, '?id=00000002').status_code == 404
    assert broken.is_dir() and (broken/'video.mp4').exists()


def test_empty_listing_and_missing_project_do_not_create_or_delete_folders(tmp_path):
    assert request(tmp_path).data == []
    assert request(tmp_path, '?id=00000000').status_code == 404
    assert not (tmp_path/'video_uploads').exists()
    assert request(tmp_path, '?id=..').status_code == 400
