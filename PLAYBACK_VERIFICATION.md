# Video playback regression (2026-09-23)

The reported regression showed a stale picture during the opening seconds,
while the waveform and frame counter advanced beyond the video's frame count.
The frame count itself was subsequently confirmed by the user: 352 frames.

## Rendering and update behavior

- The native video element renders the picture. The canvas only draws overlays.
- WaveSurfer uses an independent audio element; it does not own the review video.
- The frame counter now uses requestVideoFrameCallback's mediaTime, the timestamp
  of the presented picture, instead of the potentially advanced currentTime clock.
- A changed source creates a fresh video element and cancels the previous callback.
- Django serves the build's index.html directly with no-store headers. Its cached
  TemplateView was observed returning the previous bundle name after a rebuild.
- Playback and paused/editable landmarks share landmarkDisplayColor. Backend gait
  event colors take priority; the fallback hand wrist (index 0) stays red.

## Verification

Imported the original 001-005_Visit1_PS_L_good.mov through the local upload API.
Source and output both decoded to 352 video frames. Checked the source's opening
frames independently with FFmpeg. Tested the rebuilt frontend in the in-app
Chromium browser, on both Subject Selection and Task Selection: the correct
moving picture was visible by 0.2 seconds and playback ended at 11.778434 seconds,
with frame 351/352 (zero-based). The screencast's multi-second delay did not recur.
The original report used Firefox; this verification does not establish behavior
