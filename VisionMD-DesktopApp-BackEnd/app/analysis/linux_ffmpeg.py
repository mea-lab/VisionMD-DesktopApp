"""Provision the same verified, static FFmpeg and FFprobe on Linux."""
import fcntl
import hashlib
import os
from pathlib import Path
import platform
import shutil
import tarfile
import tempfile
import urllib.request

VERSION = '7.0.2'
ASSETS = {
    'x86_64': ('amd64', 'abda8d77ce8309141f83ab8edf0596834087c52467f6badf376a6a2a4c87cf67'),
    'aarch64': ('arm64', 'f4149bb2b0784e30e99bdda85471c9b5930d3402014e934a5098b41d0f7201b1'),
}
BASE_URL = 'https://github.com/publicala/ffmpeg-static/releases/download/v7.0.2'


def get_linux_ffmpeg():
    machine = platform.machine().lower()
    if machine not in ASSETS:
        raise RuntimeError(f'VisionMD FFmpeg is not available for Linux architecture {machine}.')
    arch, expected = ASSETS[machine]
    cache = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache') / 'visionmd' / 'ffmpeg' / f'{VERSION}-{arch}'
    cache.parent.mkdir(parents=True, exist_ok=True)
    # Use a process lock so simultaneous uploads cannot observe a partial pair.
    with (cache.parent / f'.{VERSION}-{arch}.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if all((cache / name).is_file() and os.access(cache / name, os.X_OK) for name in ('ffmpeg', 'ffprobe')):
            return str(cache / 'ffmpeg')
        filename = f'ffmpeg-{VERSION}-{arch}-static.tar.xz'
        try:
            with tempfile.TemporaryDirectory(prefix='.download-', dir=cache.parent) as temp:
                root = Path(temp)
                archive = root / filename
                digest = hashlib.sha256()
                request = urllib.request.Request(f'{BASE_URL}/{filename}', headers={'User-Agent': 'VisionMD'})
                with urllib.request.urlopen(request, timeout=60) as response, archive.open('wb') as dest:
                    while chunk := response.read(1024 * 1024):
                        digest.update(chunk)
                        dest.write(chunk)
                if digest.hexdigest() != expected:
                    raise RuntimeError('Downloaded FFmpeg archive failed its SHA-256 check.')
                staged = root / 'bin'
                staged.mkdir()
                with tarfile.open(archive, 'r:xz') as bundle:
                    for name in ('ffmpeg', 'ffprobe'):
                        members = [m for m in bundle.getmembers() if Path(m.name).name == name and m.isfile()]
                        if len(members) != 1:
                            raise RuntimeError(f'FFmpeg archive does not contain exactly one {name} binary.')
                        with bundle.extractfile(members[0]) as src, (staged / name).open('wb') as dest:
                            shutil.copyfileobj(src, dest)
                        (staged / name).chmod(0o755)
                # The lock permits replacing a partial or damaged old directory safely.
                if cache.exists():
                    shutil.rmtree(cache)
                os.replace(staged, cache)
        except Exception as exc:
            raise RuntimeError(
                f'Could not prepare VisionMD FFmpeg {VERSION}. Connect to the internet and retry; '
                f'the verified binaries are cached for later offline use. Details: {exc}'
            ) from exc
    return str(cache / 'ffmpeg')
