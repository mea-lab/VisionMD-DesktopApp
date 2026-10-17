# Upload frame-rate detection and progress

Interactive uploads first inspect compressed packet presentation timestamps with
ffprobe. This scans the complete timing sequence without decoding every picture,
sorts presentation timestamps for B-frame streams, and checks uniform spacing
with container time-base rounding tolerance. Nominal frame-rate fields alone
are not proof. Missing timestamps, discard/edit-list packets, count mismatches,
unsupported packet layouts, or variable timing fall back to the decoded check.

CFR and playback compatibility are separate checks. Compatible H.264/yuv420p MP4
inputs are used directly. A container/audio-only change copies video packets;
unsupported codecs or pixel formats are converted to H.264/yuv420p while keeping
CFR cadence. Only VFR input is retimed. Rotation follows the source display
metadata during copies and FFmpeg autorotation during encoding; upload metadata
avoids applying OpenCV autorotation a second time. Silent CFR files remain silent.

A compatible 745-frame, 1080x1920 local recording took 0.056 s for the packet
check versus 1.770 s for the decoded check (about 32x faster on this machine).
Both checks reported CFR and 745 frames. This is a timing-inspection benchmark,
not an estimate of overall upload speed or of every recording.

The upload dialog polls a per-upload status endpoint once per second and shows
elapsed time. Stages cover transfer, saving, timing inspection, conversion,
verification, and project metadata creation. Status entries expire after an hour.
The desktop server uses one process with multiple threads, so progress can be
read while the upload request runs. A multi-process deployment would require a
shared Django cache. Stage messages are not a percentage or an ETA.

Variable frame rate uploads retain the single-pass conversion and verification
below. Batch callers retain format/audio normalization unless preserve_cfr=True
is explicitly supplied.

# Single-pass video normalization

Uploads and batch analysis share `normalize_video` in `app/views/upload_video.py`.
It plans timestamp rebasing/CFR normalization, square-pixel scaling, H.264 pixel
format conversion, AAC conversion (or finite silent audio for uploads), and MP4
muxing before issuing at most one FFmpeg conversion command. Batch analysis
retains silent videos without adding an audio track.

Already compatible zero-based CFR MP4 recordings are not rewritten. When only
a container or audio change is necessary, video packets are copied. Encoding
retains the existing libx264 medium/grain/CRF-15 settings. Odd image dimensions
are padded on the bottom/right to meet yuv420p encoding requirements. The existing FFmpeg orientation behavior is retained: encoding uses default
autorotation; stream-copy operations retain source rotation metadata. Player,
thumbnail, and detector rotation handling are unchanged.

A source metadata/frame-count scan supplies the conversion plan; one output
scan verifies the result. The output must preserve frame count, start at zero,
have square pixels/H.264, and retain video duration within one frame. Replacement
happens only after verification; a failed conversion preserves the source.
Uniform timestamps are assigned by source frame index. New FFmpeg builds clear
inherited frame-duration metadata and set an explicit output rate; older builds
use passthrough synchronization to avoid repeating observations across gaps.
Tests compare the identity of every synthetic frame on both paths, as well as
counts, duration, rotation, no-op/remux behavior, and failure cleanup.

An eight-second synthetic clip with irregular timestamps, non-square pixels,
yuv444p video, and PCM audio took 4.829 s with the previous pipeline versus
2.175 s combined on the development machine (approximately 2.2x faster).
The previous upload path issued four FFmpeg passes including the remux and four
full frame scans; the new path issues one conversion pass and two full scans.
A one-time cached FFmpeg capability query is additional to those operations.
Both outputs retained all 240 frames and 8.2 s duration. This benchmark is not
an estimate of speedup for every recording: compatible recordings or those
requiring just one transformation have less redundant work to remove.

## Cross-platform command options

The packaged Windows environment pins FFmpeg 4.3.1; development binaries may be
much newer. Normalization probes runtime support for `-fps_mode` and uses legacy
`-vsync` when unavailable. Encoder time bases use explicit rational values rather
than the newer `filter` keyword. The cached setpts capability check still avoids
`strip_fps` on builds lacking that option. Regression tests inspect the legacy
commands and execute equivalent synchronization with the local FFmpeg 9 binary;
they do not constitute testing an actual Windows 4.3 binary.

The six PD gait sample recordings supplied for playback investigation are
60 fps CFR HEVC Main 10 / Dolby Vision files with AAC audio and a display rotation.
CFR detection alone therefore cannot guarantee browser playback on another OS.
The codec preparation path converts these to upright H.264/yuv420p while retaining
frame cadence and validates decoded frame count and duration before replacement.
All investigation conversions use temporary copies; source recordings are untouched.
