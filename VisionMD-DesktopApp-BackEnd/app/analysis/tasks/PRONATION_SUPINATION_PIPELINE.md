# Pronation/supination pipeline

VisionMD's pronation/supination task is a sequence pipeline, not a collection
of independent frame predictions. In the default `auto` mode its path is:

1. **Person selection.** The user-selected VisionMD subject rectangle limits
   every hand-detector search. This prevents hands belonging to clinicians,
   bystanders, and reflections from competing with the subject.
2. **Fast MediaPipe screen.** MediaPipe Hand Landmarker estimates 21 world
   landmarks at the source frame rate inside that rectangle. This result is
   accepted only with at least 95% coverage, low landmark/angle discontinuity,
   plausible range, and a passing deterministic trajectory check. Accepted
   results are explicitly marked provisional and `requires_verification`; they
   receive a review quality badge rather than being presented as validated.
3. **Automatic WiLoR fallback.** If any screen gate fails, the request
   continues automatically through the more expensive production path below.
   Users can also select `wilor` mode directly or click **Reanalyze with WiLoR**
   on a provisional result.
4. **Sparse YOLO localization.** The custom left/right hand model is sampled
   at 12 Hz. Detections are associated one-to-one between sampled frames and
   the sustained track with the most normalized motion is selected.
5. **Adaptive ROI selection.** Detection boxes are interpolated to every video
   frame. A robust fixed square is preferred when it remains compact (fixed
   side / typical dynamic side <= 1.7). Wide trajectories start with dynamic
   boxes. A fixed run that fails severe trajectory checks is rerun dynamically.
6. **Batched WiLoR.** One WiLoR instance and one YOLO instance are reused by
   the Django worker. WiLoR receives YOLO boxes directly and estimates all 21
   hand landmarks in 3-D, plus their 2-D projection for visualization.
7. **Landmark temporal decoding.** Each frame has the raw WiLoR hypothesis and
   its rigid 180-degree alternative about the wrist-to-middle-MCP axis. A
   Viterbi decoder selects a smooth sequence. A branch may change only near a
   large raw circular-angle step, and corrected intervals must have plausible
   entry and exit boundaries. This avoids turning a one-sided offset into a
   permanent winding error.
8. **Angle estimation and repair.** Geometry and palm-normal angle candidates
   are scored; the safer sequence is selected. Only bounded short flip
   intervals are repaired. Low-confidence angle samples are replaced only when
   landmark quality supplies independent evidence.
9. **Zero-phase smoothing.** A fourth-order Butterworth low-pass filter uses a
   requested 10 Hz cutoff (automatically bounded below Nyquist) and forward /
   backward filtering, so it does not introduce a time shift.
10. **VisionMD cache and plots.** Four 3-D points (wrist, index MCP, middle MCP,
   pinky MCP) and the finalized relative angle are cached per frame. All 21
   projected 2-D points are returned for video overlays. Storing the angle in
   the essential landmark record lets subrange and cycle edits reproduce the
   same signal without rerunning either neural network.
11. **Conditional BiGRU refiner.** A deterministic trajectory that fails the
   severe-quality gate is passed to a two-layer bidirectional PyTorch GRU. The
   refiner uses all raw landmarks, landmark velocities, angle candidates,
   quality features, ROI motion, and handedness. Passing trajectories never
   enter the learned model. A refined result is accepted only if it remains
   finite, does not expand range/steps beyond safety limits, and retains basic
   agreement with the deterministic signal.

## Code map

- `app/analysis/tasks/_pronation_supination.py` adapts requests, the selected
  subject rectangle, VisionMD response data, and cached re-analysis.
- `app/analysis/tasks/_mediapipe_ps_screen.py` implements the conservative fast
  screen and its explicit WiLoR-fallback gates.
- `app/analysis/tasks/_wilor_ps_pipeline.py` contains the tested tracking,
  batched inference, temporal landmark decoder, angle repair, and filter.
- `app/analysis/tasks/_wilor_temporal_refiner.py` contains V3 BiGRU feature
  construction, checkpoint loading, inference, and safety acceptance checks.
- `hand_pronation_left.py` and `hand_pronation_right.py` only select the side.

Keeping the algorithm in a private module (leading underscore) prevents the
dynamic task loader from exposing it as an API task.

WiLoR's projected 2-D landmarks are converted back to the full oriented-video
coordinate system before they are returned. VisionMD's SVG and canvas overlays
also use full-frame coordinates, so the subject/task bounding-box origin must
not be subtracted from these visualization points.

## Models and configuration

Default paths are:

- `app/analysis/models/hand_detector/best_hand_model.pt`
- `app/analysis/models/wilor_mini/pretrained_models/wilor_final.ckpt`
- `app/analysis/models/wilor_temporal/wilor_bigru_refiner_final.pt`

Deployments may override them with `VISIONMD_HAND_DETECTOR_MODEL` and
`VISIONMD_WILOR_MODEL_DIR`. The temporal checkpoint can be overridden with
`VISIONMD_PS_TEMPORAL_MODEL`. CUDA is used when PyTorch reports it available;
otherwise all models run on CPU. CPU execution is supported but much slower.

The custom hand model uses class `0` for left and class `1` for right. The
VisionMD task side determines the class; it is not inferred from screen side.

## Quality metadata

The API response includes `psPipeline.engine`, screening diagnostics, ROI mode,
localization coverage,
whether a dynamic rerun occurred, and the severe-failure diagnostics. These
checks choose between fixed and dynamic crops; they are deliberately not a
clinical validity score.

`psPipeline.temporal_refiner` records whether learned refinement was attempted,
accepted or rejected, the checkpoint/device, before/after range and maximum
step, and any rejection reason. This makes learned changes auditable.

Important limits are centralized in `_pronation_supination.py`:

- localization rate: 12 Hz
- crop scale: 1.5
- fixed/dynamic ratio: 1.7
- maximum short-flip interval: 0.6 s
- final low-pass cutoff: 10 Hz (or the safe Nyquist-bounded equivalent)

## Failure behavior

If the MediaPipe screen is rejected, that rejection is metadata rather than a
task failure: WiLoR begins automatically. WiLoR analysis stops with an
explanatory error when no hand track persists through
at least half of sampled localization frames. It does not silently switch to
the other hand. A legacy cached P/S result without the persisted final angle
must be analyzed once again with this pipeline before cached subrange editing.

When investigating a questionable result, inspect `psPipeline.quality` first,
then compare the video overlay with the signal. The raw and corrected 3-D
landmark arrays are sequence internals; adding a downloadable diagnostic file
is preferable to changing the cached response schema.

## Learned-refiner validation and limitations

V3 was trained with PyTorch on an NVIDIA GB10 using 20 manually annotated
videos and 175 accepted pseudo-labeled videos. Five-fold evaluation was grouped
by participant; pseudo-labels from each held-out participant were also removed.
Median manual RMSE improved from 12.33 to 10.71 degrees (14/20 videos improved,
6/20 worsened). This is why the production integration only attempts learned
refinement after deterministic failure and retains an output safety gate.

Pronation/supination around a forearm pointed toward a single camera can be
fundamentally ambiguous. The model may reduce winding errors but cannot create
missing depth evidence. Some videos will remain failed/manual-review cases;
the software must not present every output as valid merely because a neural
refiner returned a number.
