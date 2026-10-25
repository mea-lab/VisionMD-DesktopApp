from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os, time, cv2, json, base64
from datetime import datetime, timezone
from pymediainfo import MediaInfo
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
import subprocess
import shutil
import os, sys
import traceback
from functools import lru_cache

def get_ffmpeg_path():
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        return os.path.join(base_path, "ffmpeg")
    else:
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            raise FileNotFoundError("ffmpeg not found in PATH")
        return ffmpeg_path

def get_ffprobe_path():
    """Return the ffprobe paired with VisionMD's ffmpeg binary."""
    ffmpeg_path = get_ffmpeg_path()
    return os.path.join(os.path.dirname(ffmpeg_path), "ffprobe")

def probe_decoded_video_timing(input_path):
    """Count decoded frames and obtain their presentation duration.

    Container ``nb_frames`` and OpenCV's nominal FPS are frequently wrong for
    phone VFR recordings. ``-count_frames`` asks the decoder for the quantity
    VisionMD actually needs and lets CFR normalization preserve every frame.
    """
    cmd = [
        get_ffprobe_path(), "-v", "error", "-count_frames",
        "-select_streams", "v:0",
        "-show_entries", "stream=nb_read_frames,duration:format=duration",
        "-of", "json", input_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFprobe frame count failed:\n{result.stderr}")
    data = json.loads(result.stdout)
    if not data.get("streams"):
        raise RuntimeError("FFprobe frame count returned no video stream.")
    stream = data["streams"][0]
    frame_count = int(stream.get("nb_read_frames") or 0)
    duration = float(stream.get("duration") or data.get("format", {}).get("duration") or 0)
    if frame_count < 1 or duration <= 0:
        raise RuntimeError("FFprobe could not determine decoded frame timing.")
    return frame_count, duration

def probe_first_video_timestamp(input_path):
    """Return the presentation timestamp of the first decoded video frame."""
    cmd = [
        get_ffprobe_path(), "-v", "error", "-select_streams", "v:0",
        "-read_intervals", "%+#1",
        "-show_entries", "frame=best_effort_timestamp_time",
        "-of", "json", input_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFprobe timestamp check failed:\n{result.stderr}")
    frames = json.loads(result.stdout).get("frames") or []
    if not frames or frames[0].get("best_effort_timestamp_time") is None:
        raise RuntimeError("FFprobe returned no decoded video timestamp.")
    return float(frames[0]["best_effort_timestamp_time"])

def is_vfr(input_path):
    ffmpeg_path = get_ffmpeg_path()
    ffmprobe_path = get_ffprobe_path()
    print(f"Chosen ffmpeg binary path for ffmprobing video: {ffmprobe_path}")
    cmd = [
        ffmprobe_path,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate,avg_frame_rate",
        "-of", "json",
        input_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFprobe VFR check failed:\n{result.stderr}")

    try:
        data = json.loads(result.stdout)
        if not data.get("streams"):
            raise RuntimeError("FFprobe VFR check returned no streams.")
        stream = data["streams"][0]
        r_frame = stream.get("r_frame_rate")
        avg_frame = stream.get("avg_frame_rate")
        return r_frame != avg_frame
    except Exception:
        raise RuntimeError("Failed to parse FFprobe VFR check output.")

def convert_to_cfr(input_path, fps):
    print("Running conversion to cfr...")
    first_timestamp = probe_first_video_timestamp(input_path)
    if not is_vfr(input_path) and abs(first_timestamp) <= 0.001:
        print("Video is already zero-based CFR, skipping conversion.")
        return
    if abs(first_timestamp) > 0.001:
        print(f"Rebasing first video timestamp from {first_timestamp:.6f}s to zero.")

    base, ext = os.path.splitext(input_path)
    ffmpeg_path = get_ffmpeg_path()
    output_path = f"{base}_cfr{ext}"
    print(f"Chosen ffmpeg binary path for VFR to CFR conversion: {ffmpeg_path}")

    # Preserve the source's decoded frame count. OpenCV often reports a nominal
    # 29.97 FPS for VFR phone video even when the presentation timestamps imply
    # a different effective rate; forcing that nominal value drops frames.
    source_frame_count, source_duration = probe_decoded_video_timing(input_path)
    fps = source_frame_count / source_duration
    # Assign uniform timestamps without duplicating or dropping observations.
    # One tick per frame avoids the source's coarse or irregular clock.
    rate = f"{fps:.12f}"
    vf_value = f"settb=expr=1/({rate}),setpts=N"

    cmd = [
        f'{ffmpeg_path}', '-y',
        '-i', input_path,
        '-vf', vf_value,
        # Encoder rate is explicit; synchronization must not resample frames.
        '-enc_time_base', 'filter',
        '-fps_mode', 'passthrough',
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-tune', 'grain',
        '-crf', '15',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'copy',
        output_path
    ]
    
    print(f"Subprocess.CREATE_NO_WINDOW value: {getattr(subprocess, 'CREATE_NO_WINDOW', 0)}")
    result = subprocess.run(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg CFR conversion failed:\n{result.stderr.decode('utf-8')}")
    
    converted_count, _ = probe_decoded_video_timing(output_path)
    if converted_count != source_frame_count:
        raise RuntimeError(
            f"CFR normalization changed decoded frames from {source_frame_count} "
            f"to {converted_count}; source file was preserved."
        )
    converted_start = probe_first_video_timestamp(output_path)
    if abs(converted_start) > 0.001:
        raise RuntimeError(
            "CFR normalization did not produce zero-based video timestamps "
            f"(first frame is {converted_start:.6f}s); source file was preserved."
        )
    os.replace(output_path, input_path)

def convert_to_square_pixels(input_path):
    print("Running conversion to square pixels...")
    ffmpeg_path = get_ffmpeg_path()
    ffprobe_path = get_ffprobe_path()
    cmd = [
        ffprobe_path,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,sample_aspect_ratio,display_aspect_ratio",
        "-of", "json",
        input_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFprobe failed:\n{result.stderr}")

    data = json.loads(result.stdout)
    if not data.get("streams"):
        raise RuntimeError("FFprobe returned no video streams.")
    stream = data["streams"][0]
    width = stream.get("width")
    height = stream.get("height")
    sar = stream.get("sample_aspect_ratio")
    dar = stream.get("display_aspect_ratio")

    def parse_ratio(ratio):
        if not ratio or ratio in {"0:1", "N/A"}:
            return None
        try:
            num_str, den_str = ratio.split(":")
            num = float(num_str)
            den = float(den_str)
            if den == 0:
                return None
            return num / den
        except Exception:
            return None

    sar_ratio = parse_ratio(sar)
    dar_ratio = parse_ratio(dar)
    if width and height and (sar in {"1:1", "N/A", None}):
        pixel_ratio = width / height
        if dar_ratio is None or abs(pixel_ratio - dar_ratio) < 0.001:
            print("Video already has square pixels and SAR matches DAR, skipping normalization.")
            return input_path

    if width is None or height is None:
        raise RuntimeError("Could not read video dimensions for square pixel normalization.")

    if sar_ratio is None:
        sar_ratio = 1.0

    target_w = width
    target_h = height
    if sar_ratio != 1.0:
        target_w = int(round(width * sar_ratio))
    elif dar_ratio is not None:
        target_w = int(round(height * dar_ratio))
    else:
        print("No DAR reported and SAR is 1:1, skipping normalization.")
        return input_path

    if target_w % 2 != 0:
        target_w += 1

    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_square{ext}"
    vf_filter = f"scale={target_w}:{target_h},setsar=1"
    cmd = [
        f"{ffmpeg_path}", "-y",
        "-i", input_path,
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "medium",
        "-tune", "grain",
        "-crf", "15",
        "-pix_fmt", "yuv420p",
        "-fps_mode", "passthrough",
        "-c:a", "copy",
        output_path
    ]
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg square pixel normalization failed:\n{result.stderr.decode('utf-8')}")

    os.remove(input_path)
    os.rename(output_path, input_path)
    return input_path

def convert_to_h264_aac(input_path):
    print("Running conversion to h264 aac encoding...")
    ffmpeg_path = get_ffmpeg_path()
    ffprobe_path = get_ffprobe_path()

    probe_cmd = [
        ffprobe_path,
        "-v", "error",
        "-show_entries", "stream=index,codec_type,codec_name,pix_fmt",
        "-of", "json",
        input_path,
    ]
    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
    if probe_result.returncode != 0:
        raise RuntimeError(f"FFprobe codec check failed:\n{probe_result.stderr}")

    probe_data = json.loads(probe_result.stdout)
    streams = probe_data.get("streams") or []
    video_codec = None
    audio_codec = None
    video_pix_fmt = None
    for stream in streams:
        if stream.get("codec_type") == "video" and video_codec is None:
            video_codec = stream.get("codec_name")
            video_pix_fmt = stream.get("pix_fmt")
        elif stream.get("codec_type") == "audio" and audio_codec is None:
            audio_codec = stream.get("codec_name")

    if video_codec is None:
        raise RuntimeError("Input has no video stream for H.264 conversion.")
    if audio_codec is None:
        raise RuntimeError("Input has no audio stream for AAC conversion.")
    acceptable_pix_fmts = {"yuv420p", "yuvj420p"}
    if video_codec == "h264" and audio_codec == "aac" and video_pix_fmt in acceptable_pix_fmts:
        print("Video is already encoded with H.264/AAC and yuv420p, skipping codec conversion.")
        return input_path

    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_h264_aac{ext}"

    cmd = [
        f"{ffmpeg_path}", "-y",
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", "medium",
        "-tune", "grain",
        "-crf", "15",
        "-pix_fmt", "yuv420p",
        "-fps_mode", "passthrough",
        "-profile:v", "main",
        "-level", "4.0",
        "-c:a", "aac",
        "-b:a", "128k",
        output_path
    ]
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg H.264/AAC transcode failed:\n{result.stderr.decode('utf-8')}")

    verify_cmd = [
        ffprobe_path,
        "-v", "error",
        "-show_entries", "stream=codec_type,codec_name,pix_fmt",
        "-of", "json",
        output_path,
    ]
    verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
    if verify_result.returncode != 0:
        raise RuntimeError(f"FFprobe verification failed:\n{verify_result.stderr}")

    verify_data = json.loads(verify_result.stdout)
    verify_streams = verify_data.get("streams") or []
    out_video_codec = None
    out_audio_codec = None
    out_video_pix_fmt = None
    for stream in verify_streams:
        if stream.get("codec_type") == "video" and out_video_codec is None:
            out_video_codec = stream.get("codec_name")
            out_video_pix_fmt = stream.get("pix_fmt")
        elif stream.get("codec_type") == "audio" and out_audio_codec is None:
            out_audio_codec = stream.get("codec_name")

    if out_video_codec != "h264" or out_audio_codec != "aac" or out_video_pix_fmt not in acceptable_pix_fmts:
        raise RuntimeError(
            "Transcode verification failed. "
            f"Got video={out_video_codec}, audio={out_audio_codec}, pix_fmt={out_video_pix_fmt}."
        )

    os.replace(output_path, input_path)
    return input_path

def convert_to_mp4(input_path):
    print("Running conversion to mp4...")

    ffmpeg_path = get_ffmpeg_path()
    ffprobe_path = get_ffprobe_path()

    if not os.path.exists(input_path):
        raise RuntimeError(f"Input video file does not exist: {input_path}")

    base, ext = os.path.splitext(input_path)
    target_path = f"{base}.mp4"
    if ext.lower() == ".mp4":
        print("Video is already mp4, skipping mp4 conversion.")
        return input_path
    if os.path.abspath(input_path) == os.path.abspath(target_path):
        output_path = f"{base}_tmp.mp4"
    else:
        output_path = target_path

    # Earlier upload steps guarantee H.264/yuv420p video and AAC audio.
    # A container change must be lossless: re-encoding here used to compress
    # every non-MP4 upload twice and visibly softened fingertip detail.
    cmd = [
        f"{ffmpeg_path}", "-y",
        "-i", input_path,
        "-map", "0:v:0",
        "-map", "0:a:0?",
        "-c", "copy",
        "-movflags", "+faststart",
        output_path,
    ]
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg MP4 transcode failed:\n{result.stderr.decode('utf-8')}")

    verify_cmd = [
        ffprobe_path,
        "-v", "error",
        "-show_entries", "format=format_name",
        "-show_entries", "stream=codec_type,codec_name,pix_fmt",
        "-of", "json",
        output_path,
    ]
    verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
    if verify_result.returncode != 0:
        raise RuntimeError(f"FFprobe MP4 verification failed:\n{verify_result.stderr}")

    try:
        verify_data = json.loads(verify_result.stdout)
    except Exception as e:
        raise RuntimeError(f"Failed to parse FFprobe MP4 verification output: {e}")

    format_name = (verify_data.get("format") or {}).get("format_name") or ""
    if "mp4" not in format_name.split(","):
        raise RuntimeError(f"Output container is not MP4 (format_name={format_name}).")

    streams = verify_data.get("streams") or []
    out_video_codec = None
    out_audio_codec = None
    out_video_pix_fmt = None
    for stream in streams:
        if stream.get("codec_type") == "video" and out_video_codec is None:
            out_video_codec = stream.get("codec_name")
            out_video_pix_fmt = stream.get("pix_fmt")
        elif stream.get("codec_type") == "audio" and out_audio_codec is None:
            out_audio_codec = stream.get("codec_name")

    acceptable_pix_fmts = {"yuv420p", "yuvj420p"}
    if out_video_codec != "h264" or out_video_pix_fmt not in acceptable_pix_fmts:
        raise RuntimeError(
            "MP4 transcode verification failed. "
            f"Got video={out_video_codec}, pix_fmt={out_video_pix_fmt}."
        )
    if out_audio_codec is not None and out_audio_codec != "aac":
        raise RuntimeError(f"MP4 transcode verification failed. Got audio={out_audio_codec}.")

    if os.path.abspath(input_path) == os.path.abspath(target_path):
        os.replace(output_path, target_path)
        saved_video_path = target_path
    else:
        if os.path.exists(input_path):
            os.remove(input_path)
        saved_video_path = output_path

    return saved_video_path

def add_dummy_audio_if_missing(video_path):
    ffmpeg_path = get_ffmpeg_path()
    ffprobe_path = get_ffprobe_path()

    probe_cmd = [
        ffprobe_path,
        "-v", "error",
        "-show_entries", "stream=codec_type",
        "-of", "json",
        video_path,
    ]
    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
    if probe_result.returncode != 0:
        raise RuntimeError(f"FFprobe audio stream check failed:\n{probe_result.stderr}")

    try:
        probe_data = json.loads(probe_result.stdout)
    except Exception as e:
        raise RuntimeError(f"Failed to parse FFprobe audio stream output: {e}")

    streams = probe_data.get("streams") or []
    has_audio_stream = any(stream.get("codec_type") == "audio" for stream in streams)
    if has_audio_stream:
        return video_path

    base, ext = os.path.splitext(video_path)
    output_path = f"{base}_with_dummy_audio{ext}"

    cmd = [
        ffmpeg_path, "-y",
        "-i", video_path,
        "-f", "lavfi",
        "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        output_path,
    ]
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg dummy audio injection failed:\n{result.stderr.decode('utf-8')}")

    os.replace(output_path, video_path)
    return video_path

def get_rotation(path):
    mi = MediaInfo.parse(path)
    for track in mi.tracks:
        if track.track_type == "Video" and getattr(track, 'rotation', None):
            try:
                return int(float(track.rotation))
            except ValueError:
                pass

    parser = createParser(path)
    if parser:
        meta = extractMetadata(parser)
        if meta and meta.has("rotation"):
            try:
                return int(meta.get("rotation").value)
            except Exception:
                pass

    return 0


@lru_cache(maxsize=4)
def _supports_strip_fps(ffmpeg_path):
    result = subprocess.run([ffmpeg_path, '-hide_banner', '-h', 'filter=setpts'],
                            capture_output=True, text=True,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    return result.returncode == 0 and 'strip_fps' in result.stdout


def _normalization_probe(input_path):
    """Read normalization metadata and count frames in one decode pass."""
    cmd = [get_ffprobe_path(), '-v', 'error', '-count_frames',
           '-show_streams', '-show_format', '-of', 'json', input_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"FFprobe normalization check failed:\n{result.stderr}")
    data = json.loads(result.stdout)
    video = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), None)
    if video is None:
        raise RuntimeError('Input has no video stream.')
    count = int(video.get('nb_read_frames') or 0)
    duration = float(video.get('duration') or data.get('format', {}).get('duration') or 0)
    if count < 1 or not duration > 0:
        raise RuntimeError('Could not determine decoded video frame timing.')
    audio = next((s for s in data.get('streams', []) if s.get('codec_type') == 'audio'), None)
    return {'video': video, 'audio': audio, 'frame_count': count, 'duration': duration}


def _square_pixel_size(video):
    width, height = int(video['width']), int(video['height'])
    def ratio(value):
        try:
            a, b = value.split(':')
            return float(a) / float(b)
        except (AttributeError, ValueError, ZeroDivisionError):
            return None
    sar = ratio(video.get('sample_aspect_ratio'))
    dar = ratio(video.get('display_aspect_ratio'))
    if sar is None:
        sar = dar * height / width if dar else 1.0
    if abs(sar - 1.0) < .001:
        return None
    target_width = max(2, int(round(width * sar)))
    return target_width + target_width % 2, height


def normalize_video(input_path, add_audio=True):
    """Normalize in at most one FFmpeg pass, preserving decoded video frames.

    Keep the current libx264 quality settings. Compatible zero-based CFR MP4
    streams are left untouched; container/audio-only changes copy video packets.
    Two full frame scans suffice when conversion is needed (source and output).
    Preserve the previous FFmpeg orientation behavior: encoding autorotates
    pixels, while stream-copy operations retain the source display metadata.
    """
    source = _normalization_probe(input_path)
    video, audio = source['video'], source['audio']
    count, duration = source['frame_count'], source['duration']
    first_timestamp = probe_first_video_timestamp(input_path)
    retime = (video.get('r_frame_rate') != video.get('avg_frame_rate')
              or abs(first_timestamp) > .001)
    geometry = dict(video)
    rotation = next((float(item['rotation']) for item in video.get('side_data_list', [])
                     if 'rotation' in item), float(video.get('tags', {}).get('rotate', 0)))
    if abs(rotation) % 180 == 90:
        # Plan scaling on the pixels produced by the existing FFmpeg autorotation.
        geometry['width'], geometry['height'] = video['height'], video['width']
        for key in ('sample_aspect_ratio', 'display_aspect_ratio'):
            value = video.get(key, '')
            if ':' in value:
                a, b = value.split(':')
                geometry[key] = f'{b}:{a}'
    square_size = _square_pixel_size(geometry)
    encode_video = (retime or square_size is not None
                    or video.get('codec_name') != 'h264'
                    or video.get('pix_fmt') not in {'yuv420p', 'yuvj420p'}
                    or int(video['width']) % 2 or int(video['height']) % 2)
    encode_audio = audio is not None and (audio.get('codec_name') != 'aac'
                                        or abs(first_timestamp) > .001)
    dummy_audio = audio is None and add_audio
    base, ext = os.path.splitext(input_path)
    summary = {'path': input_path, 'source_frame_count': count,
               'source_duration': duration, 'frame_count': count, 'duration': duration}
    if not (encode_video or encode_audio or dummy_audio) and ext.lower() == '.mp4':
        return summary

    # Write a separate file and verify before touching the source.
    target = f'{base}.mp4'
    import tempfile
    fd, output = tempfile.mkstemp(prefix='visionmd-normalize-', suffix='.mp4',
                                  dir=os.path.dirname(os.path.abspath(input_path)))
    os.close(fd)
    cmd = [get_ffmpeg_path(), '-v', 'error', '-y', '-i', input_path]
    if dummy_audio:
        # A finite audio source avoids -shortest truncating the final video frame.
        cmd += ['-f', 'lavfi', '-i',
                f'anullsrc=channel_layout=stereo:sample_rate=48000:d={duration:.12f}']
    cmd += ['-map', '0:v:0']
    if dummy_audio:
        cmd += ['-map', '1:a:0']
    elif audio is not None:
        cmd += ['-map', '0:a:0']
    filters = []
    strip_fps = False
    if retime:
        rate = f'{count / duration:.12f}'
        # Assign one exact tick per source frame and remove obsolete source
        # frame-duration metadata before CFR synchronization.
        strip_fps = _supports_strip_fps(cmd[0])
        pts_filter = 'setpts=N:strip_fps=1' if strip_fps else 'setpts=N'
        filters += [f'settb=expr=1/({rate})', pts_filter]
    if square_size is not None:
        filters += [f'scale={square_size[0]}:{square_size[1]}', 'setsar=1']
    if int(video['width']) % 2 or int(video['height']) % 2:
        filters += ['pad=ceil(iw/2)*2:ceil(ih/2)*2']
    if encode_video:
        if filters:
            cmd += ['-vf', ','.join(filters)]
        if retime:
            cmd += ['-enc_time_base', 'filter']
            if strip_fps:
                cmd += ['-r', rate]
            # Older builds cannot clear inherited frame durations: passthrough
            # preserves each observation, rather than resampling those durations.
        cmd += ['-fps_mode', 'cfr' if retime and strip_fps else 'passthrough', '-c:v', 'libx264',
                '-preset', 'medium', '-tune', 'grain', '-crf', '15',
                '-pix_fmt', 'yuv420p']
    else:
        cmd += ['-c:v', 'copy']
    if audio is not None or dummy_audio:
        cmd += ['-c:a', 'aac' if encode_audio or dummy_audio else 'copy']
        if encode_audio or dummy_audio:
            cmd += ['-b:a', '128k']
        if encode_audio and abs(first_timestamp) > .001:
            cmd += ['-af', 'asetpts=PTS-STARTPTS']
    cmd += ['-movflags', '+faststart', output]
    try:
        result = subprocess.run(cmd, capture_output=True,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise RuntimeError(f"FFmpeg normalization failed:\n{result.stderr.decode('utf-8', errors='replace')}")
        normalized = _normalization_probe(output)
        if normalized['frame_count'] != count:
            raise RuntimeError(f"Normalization changed decoded frames from {count} "
                               f"to {normalized['frame_count']}; source file was preserved.")
        if abs(probe_first_video_timestamp(output)) > .001:
            raise RuntimeError('Normalization did not produce zero-based video timestamps; source file was preserved.')
        if abs(normalized['duration'] - duration) >= duration / count:
            raise RuntimeError('Normalization changed video duration by at least one frame; source file was preserved.')
        if _square_pixel_size(normalized['video']) is not None:
            raise RuntimeError('Normalization did not produce square pixels; source file was preserved.')
        if normalized['video'].get('codec_name') != 'h264':
            raise RuntimeError('Normalization did not produce H.264 video; source file was preserved.')
        if add_audio and (normalized['audio'] is None or normalized['audio'].get('codec_name') != 'aac'):
            raise RuntimeError('Normalization did not produce AAC audio; source file was preserved.')
        os.replace(output, target)
        if os.path.abspath(input_path) != os.path.abspath(target):
            os.remove(input_path)
        summary.update(path=target, duration=normalized['duration'])
        return summary
    finally:
        if os.path.exists(output):
            os.remove(output)


@api_view(['POST'])
def upload_video(request):
    try:
        print("Started processing video upload...")
        if 'video' not in request.FILES:
            return Response(
                {"detail": "'video' field missing or no files uploaded."},
                status=400
            )

        # Determine the base directory where all project‐ID folders live
        upload_root = os.path.join(settings.MEDIA_ROOT, "video_uploads")
        os.makedirs(upload_root, exist_ok=True)

        # Build a set of existing project‐IDs (folders named as 8-digit strings)
        existing_ids = set()
        for name in os.listdir(upload_root):
            full_path = os.path.join(upload_root, name)
            if os.path.isdir(full_path) and name.isdigit() and len(name) == 8:
                existing_ids.add(int(name))

        # Find the lowest unused integer between 0 and 99,999,999
        new_id_int = None
        for candidate in range(0, 100_000_000):
            if candidate not in existing_ids:
                new_id_int = candidate
                break
        if new_id_int is None:
            return Response(
                {"detail": "All project IDs from 00000000 through 99999999 are already taken."},
                status=500
            )

        # Zero-pad to 8 digits
        new_id_str = f"{new_id_int:08d}"

        # Create a folder named by the new project ID
        folder_path = os.path.join(upload_root, new_id_str)
        os.makedirs(folder_path, exist_ok=True)

        # Save the uploaded video file into that folder
        video = request.FILES['video']
        original_filename = video.name
        fs = FileSystemStorage(location=folder_path)
        saved_name = fs.save(original_filename, video)
        saved_video_path = os.path.join(folder_path, saved_name)
        if not os.path.exists(saved_video_path):
            raise RuntimeError("Video file was not saved to disk.")
        stem_name, extension = os.path.splitext(original_filename)
        file_type = extension.lstrip('.')

        cap = cv2.VideoCapture(saved_video_path)
        if not cap.isOpened():
            return Response("Cannot open video file after saving.", status=400)
        ret, frame = cap.read()
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        if not ret or frame is None:
            raise RuntimeError("Failed to read a frame from the uploaded video.")
        if not fps or fps <= 0:
            raise RuntimeError(f"Invalid FPS detected: {fps}")

        # Capture the source's decoded video frames before any normalization.
        # This is the invariant that matters; nominal FPS and container
        # ``nb_frames`` fields are not reliable for VFR phone recordings.
        normalized = normalize_video(saved_video_path)
        saved_video_path = normalized['path']
        source_frame_count = normalized['source_frame_count']
        source_duration = normalized['source_duration']
        original_filename = os.path.basename(saved_video_path)
        file_type = os.path.splitext(original_filename)[1].lstrip('.')
        cap2 = cv2.VideoCapture(saved_video_path)
        ret, frame = cap2.read()
        cap2.release()
        frame_count, decoded_duration = normalized["frame_count"], normalized["duration"]
        fps = frame_count / decoded_duration
        if frame_count != source_frame_count:
            raise RuntimeError(
                "Video normalization changed the decoded frame count "
                f"from {source_frame_count} to {frame_count}. The upload was "
                "stopped rather than saving an incomplete working video."
            )
        if not ret or frame is None:
            raise RuntimeError("Failed to read a frame after normalization.")
        if not fps or fps <= 0:
            raise RuntimeError(f"Invalid FPS after normalization: {fps}")

        rotation = get_rotation(saved_video_path)
        rotation_map = {
            90: cv2.ROTATE_90_CLOCKWISE,
            180: cv2.ROTATE_180,
            270: cv2.ROTATE_90_COUNTERCLOCKWISE
        }
        if rotation in rotation_map:
            frame = cv2.rotate(frame, rotation_map[rotation])

        success, buffer = cv2.imencode('.jpg', frame)
        if not success:
            return Response({"detail": "Failed to encode thumbnail as JPEG."}, status=500)

        thumbnail_rel_name = "thumbnail.jpg"
        thumbnail_path = os.path.join(folder_path, thumbnail_rel_name)
        with open(thumbnail_path, 'wb') as f:
            f.write(buffer)

        video_url = os.path.join(settings.MEDIA_URL, "video_uploads", new_id_str, original_filename)
        thumbnail_url = os.path.join(settings.MEDIA_URL, "video_uploads", new_id_str, thumbnail_rel_name)

        # Assemble metadata
        metadata = {
            "id": new_id_str,
            "video_name": original_filename,
            "stem_name": stem_name,
            "file_type": file_type,
            "fps": fps,
            "frame_count": frame_count,
            "source_frame_count": source_frame_count,
            "source_duration": source_duration,
            "thumbnail_url": thumbnail_url,
            "video_url": video_url,
            "rotation": rotation,
            "last_edited": datetime.now(timezone.utc).isoformat()
        }
        
        metadata_wrapped = {
            "metadata": metadata
        }

        # Save metadata.json into the same folder
        metadata_path = os.path.join(folder_path, 'metadata.json')
        with open(metadata_path, 'w') as jf:
            json.dump(metadata_wrapped, jf, indent=4)

        # Return the metadata as JSON
        return Response(metadata_wrapped, status=200)
    except Exception as e:
        print(traceback.format_exc())
        return Response({"detail": f"{e}"}, status=500)
