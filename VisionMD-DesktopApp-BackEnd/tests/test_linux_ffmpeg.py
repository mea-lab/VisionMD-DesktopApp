import hashlib
import io
import tarfile
from pathlib import Path
from unittest.mock import patch
import pytest
from app.analysis import linux_ffmpeg


def make_archive():
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w:xz') as bundle:
        for name in ('ffmpeg', 'ffprobe'):
            contents = f'{name} binary'.encode()
            info = tarfile.TarInfo(f'ffmpeg-7.0.2-arm64-static/{name}')
            info.size = len(contents)
            bundle.addfile(info, io.BytesIO(contents))
    return data.getvalue()


def test_verified_pair_is_cached_and_reused(tmp_path, monkeypatch):
    archive = make_archive()
    monkeypatch.setenv('XDG_CACHE_HOME', str(tmp_path))
    monkeypatch.setattr(linux_ffmpeg.platform, 'machine', lambda: 'aarch64')
    monkeypatch.setitem(linux_ffmpeg.ASSETS, 'aarch64', ('arm64', hashlib.sha256(archive).hexdigest()))
    with patch.object(linux_ffmpeg.urllib.request, 'urlopen', return_value=io.BytesIO(archive)) as download:
        ffmpeg = Path(linux_ffmpeg.get_linux_ffmpeg())
        assert ffmpeg.read_bytes() == b'ffmpeg binary'
        assert ffmpeg.with_name('ffprobe').read_bytes() == b'ffprobe binary'
        assert linux_ffmpeg.get_linux_ffmpeg() == str(ffmpeg)
        assert download.call_count == 1


def test_rejects_unverified_download(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CACHE_HOME', str(tmp_path))
    monkeypatch.setattr(linux_ffmpeg.platform, 'machine', lambda: 'aarch64')
    with patch.object(linux_ffmpeg.urllib.request, 'urlopen', return_value=io.BytesIO(make_archive())):
        with pytest.raises(RuntimeError, match='SHA-256'):
            linux_ffmpeg.get_linux_ffmpeg()
    assert not (tmp_path / 'visionmd' / 'ffmpeg' / '7.0.2-arm64' / 'ffmpeg').exists()
