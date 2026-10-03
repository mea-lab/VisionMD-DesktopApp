import hashlib
import subprocess
from pathlib import Path

import pytest

from app.views.upload_video import normalize_video, get_ffmpeg_path, get_ffprobe_path
import importlib
module = importlib.import_module('app.views.upload_video')


def generate(source, *extra):
    subprocess.run([get_ffmpeg_path(), '-v', 'error', '-y', '-f', 'lavfi',
                    '-i', 'testsrc2=size=160x120:rate=30', *extra, str(source)], check=True)


def recording_commands(monkeypatch):
    commands = []
    original = module.subprocess.run
    def run(cmd, *args, **kwargs):
        commands.append(cmd)
        return original(cmd, *args, **kwargs)
    monkeypatch.setattr(module.subprocess, 'run', run)
    return commands


def test_all_transformations_use_one_encode_and_two_frame_scans(tmp_path, monkeypatch):
    source = tmp_path / 'combined.mov'
    generate(source, '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000',
             '-frames:v', '90', '-vf', 'setsar=5/4,setpts=PTS+0.2/TB*gte(N\\,40)',
             '-fps_mode', 'passthrough', '-c:v', 'libx264', '-pix_fmt', 'yuv444p',
             '-c:a', 'pcm_s16le', '-shortest')
    commands = recording_commands(monkeypatch)
    result = normalize_video(str(source))
    encodes = [c for c in commands if c[0] == get_ffmpeg_path() and '-i' in c]
    scans = [c for c in commands if '-count_frames' in c]
    assert len(encodes) == 1 and len(scans) == 2
    cmd = encodes[0]
    vf = cmd[cmd.index('-vf') + 1]
    assert 'setpts=N' in vf and 'scale=200:120,setsar=1' in vf
    assert result['source_frame_count'] == result['frame_count'] == 90
    output = module._normalization_probe(result['path'])
    assert output['video']['width'] == 200 and output['video']['height'] == 120
    assert output['video']['pix_fmt'] == 'yuv420p'
    assert output['audio']['codec_name'] == 'aac'
    assert not source.exists()


def test_compatible_mov_remux_and_silent_audio_do_not_encode_video(tmp_path, monkeypatch):
    source = tmp_path / 'silent.mov'
    generate(source, '-frames:v', '30', '-c:v', 'libx264', '-pix_fmt', 'yuv420p')
    commands = recording_commands(monkeypatch)
    result = normalize_video(str(source))
    encodes = [c for c in commands if c[0] == get_ffmpeg_path() and '-i' in c]
    assert len(encodes) == 1
    assert encodes[0][encodes[0].index('-c:v') + 1] == 'copy'
    assert '-shortest' not in encodes[0]
    assert result['frame_count'] == 30
    commands.clear()
    second = normalize_video(result['path'])
    assert second['path'] == result['path']
    assert not any(c[0] == get_ffmpeg_path() for c in commands)
    assert sum('-count_frames' in c for c in commands) == 1


@pytest.mark.parametrize('retime', [False, True])
@pytest.mark.parametrize('angle', [90, 180, 270])
@pytest.mark.parametrize('sar', ['1/1', '5/4'])
def test_rotated_recording_matches_previous_display_behavior(tmp_path, retime, angle, sar):
    plain = tmp_path / 'plain.mp4'
    vf = f'setsar={sar}' + (',setpts=PTS+0.2/TB' if retime else '')
    extra = ['-vf', vf, '-fps_mode', 'passthrough']
    generate(plain, '-frames:v', '30', *extra, '-c:v', 'libx264', '-pix_fmt', 'yuv420p')
    source = tmp_path / 'rotated.mov'
    help_text = subprocess.check_output([get_ffmpeg_path(), '-hide_banner', '-h', 'full'],
                                        stderr=subprocess.DEVNULL, text=True)
    if '-display_rotation' in help_text:
        cmd = [get_ffmpeg_path(), '-v', 'error', '-y', '-copyts', '-display_rotation', str(angle),
               '-noautorotate', '-i', str(plain), '-c', 'copy', str(source)]
    else:
        cmd = [get_ffmpeg_path(), '-v', 'error', '-y', '-copyts', '-i', str(plain),
               '-c', 'copy', '-metadata:s:v:0', f'rotate={angle}', str(source)]
    subprocess.run(cmd, check=True)
    def displayed_first_frame(path):
        import numpy as np
        # FFmpeg's default display orientation is the old conversion behavior.
        frame = subprocess.check_output([get_ffmpeg_path(), '-v', 'error', '-i', str(path),
                    '-vf', 'scale=trunc(iw*sar/2)*2:ih,setsar=1',
                    '-frames:v', '1', '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-'])
        return np.frombuffer(frame, dtype=np.uint8).astype(float)
    def rotation(path):
        video = module._normalization_probe(str(path))['video']
        return next((s['rotation'] for s in video.get('side_data_list', []) if 'rotation' in s), 0)
    assert (module.probe_first_video_timestamp(str(source)) > .1) == retime
    before = displayed_first_frame(source)
    source_rotation = rotation(source)
    output = normalize_video(str(source))
    after = displayed_first_frame(output['path'])
    import numpy as np
    assert np.mean(np.abs(after - before)) < 5
    assert rotation(output['path']) == (0 if retime or sar != '1/1' else source_rotation)
    assert output['frame_count'] == 30


def test_failed_verification_preserves_source(tmp_path, monkeypatch):
    source = tmp_path / 'safe.mov'
    generate(source, '-frames:v', '30', '-c:v', 'libx264')
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    probe = module._normalization_probe
    def bad_probe(path):
        result = probe(path)
        if Path(path).name.startswith('visionmd-normalize-'):
            result['frame_count'] -= 1
        return result
    monkeypatch.setattr(module, '_normalization_probe', bad_probe)
    with pytest.raises(RuntimeError, match='source file was preserved'):
        normalize_video(str(source))
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    assert not (tmp_path / 'safe.mp4').exists()
    assert not list(tmp_path.glob('visionmd-normalize-*'))


def test_low_rate_odd_sized_webm_preserves_duration_and_frame_spacing(tmp_path):
    source = tmp_path / 'odd.webm'
    subprocess.run([get_ffmpeg_path(), '-v', 'error', '-y', '-f', 'lavfi',
                    '-i', 'testsrc=size=161x121:rate=7', '-frames:v', '15',
                    '-c:v', 'libvpx', '-pix_fmt', 'yuv420p', str(source)], check=True)
    from app.views.upload_video import probe_decoded_video_timing
    before_count, before_duration = probe_decoded_video_timing(str(source))
    result = normalize_video(str(source))
    assert result['frame_count'] == before_count == 15
    assert result['duration'] == pytest.approx(before_duration, abs=.001)
    v = module._normalization_probe(result['path'])['video']
    assert (v['width'], v['height']) == (162, 122)


@pytest.mark.parametrize('strip_fps', [False, True])
def test_retiming_preserves_every_frame_identity(tmp_path, monkeypatch, strip_fps):
    source = tmp_path / 'indexed.mov'
    # Each source frame has a distinct gray level, allowing detection of repeated
    # or omitted observations even when the output count would happen to match.
    generate(source, '-frames:v', '60', '-vf',
             'geq=lum=16+N*3:cb=128:cr=128,setpts=PTS+0.2/TB*gte(N\\,30)',
             '-fps_mode', 'passthrough', '-c:v', 'libx264', '-crf', '0')
    def levels(path):
        import numpy as np
        pixels = subprocess.check_output([get_ffmpeg_path(), '-v', 'error',
                    '-noautorotate', '-i', str(path), '-map', '0:v:0',
                    '-fps_mode', 'passthrough', '-pix_fmt', 'gray', '-f', 'rawvideo', '-'])
        return np.frombuffer(pixels, dtype=np.uint8).reshape(-1,120,160).mean(axis=(1,2))
    before = levels(source)
    if strip_fps and not module._supports_strip_fps(get_ffmpeg_path()):
        pytest.skip('This FFmpeg does not support strip_fps')
    monkeypatch.setattr(module, '_supports_strip_fps', lambda _path: strip_fps)
    result = normalize_video(str(source))
    after = levels(result['path'])
    import numpy as np
    np.testing.assert_allclose(after, before, atol=1)
    assert result['frame_count'] == 60
