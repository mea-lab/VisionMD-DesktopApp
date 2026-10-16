# Upload frame-rate detection and progress

Interactive uploads inspect every decoded video frame timestamp during the source
scan. CFR detection checks monotonic timestamps and uniform spacing, allowing
container time-base rounding; nominal r_frame_rate/avg_frame_rate equality alone
is not sufficient. CFR uploads use the original file unchanged, including its
container, audio, and timestamp origin. No conversion or output verification scan
is performed for these uploads. The initial timing scan still takes time on long
recordings.

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
