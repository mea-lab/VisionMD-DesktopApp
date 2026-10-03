# Single-pass video normalization

Uploads and batch analysis share `normalize_video` in `app/views/upload_video.py`.
It plans timestamp rebasing/CFR normalization, square-pixel scaling, H.264 pixel
format conversion, AAC conversion (or finite silent audio for uploads), and MP4
muxing before issuing at most one FFmpeg conversion command. Batch analysis
retains silent videos without adding an audio track.

Already compatible zero-based CFR MP4 recordings are not rewritten. When only
a container or audio change is necessary, video packets are copied. Encoding
retains the existing libx264 medium/grain/CRF-15 settings. Odd image dimensions
are padded on the bottom/right to meet yuv420p encoding requirements. Rotation
metadata is retained, rather than baking a rotation into the sensor pixels.

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
