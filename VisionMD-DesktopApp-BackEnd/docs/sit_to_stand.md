# Sit-to-stand task

The user-visible task is **Sit-to-stand**. Its canonical value is `Sit To Stand`,
module/endpoint `sit_to_stand`, and class `SitToStandTask`. The canonical value
uses spaces so the existing discovery and reload conventions remain valid.
The task is registered in `taskOptions.jsx` and has both required frontend views.

## Selection and acquisition

The selection component reuses gait's timing, camera editor and participant-height
controls, including centimeters and feet/inches. The existing height prompt covers
this task in selection, direct analysis, and analysis dialogs; the background API
also rejects invalid height. Camera fields remain optional, as with gait. Shared
camera parsing preserves fractional FOV, focal length and pixel size, and generated
intrinsics use a valid homogeneous bottom row.

Record a single frontal rise with an initial seated baseline and a final standing
hold. The subject's head, feet and arms should remain visible. The task shares
`GaitTask`'s full-frame MeTRAbs input, subject tracking, cancellation and device
fallback, but does not run gait phase inference. It uses `mpi_inf_3dhp_17` and
retains video-space XY for the existing video landmark overlays. Source videos
are never removed. Tracking gaps longer than 0.5 s or over 10% of frames stop
analysis; shorter repairs are reported.

Height and camera inputs are retained with the result. No metric displacement
or height-derived scaling is reported in this version: that requires an eligible,
upright full-body reference and a validated calibration method. Normalized
shoulder-to-ankle reference length is not the person's stature. The optional
visibility metadata does not itself establish an upright reference.

## Measurements

The implementation in `tasks/_sit_to_stand.py` ports the study's 10 selected
features, excluding SPARC, jerk and pause fraction:

1. Candidate-local 10–90% ankle-relative pelvis ascent time (seconds).
2. Signed normalized ascent velocity coefficient of variation (population SD/mean).
3. Lateral pelvis range relative to ankle midpoint, divided by reference length.
4. Frontal trunk lateral angular range (degrees).
5. Ankle-relative pelvis endpoint excursion, divided by reference length.
6. Mean wrist-to-opposite-shoulder distance, normalized by shoulder width.
7. Range of that crossed-arm distance.
8. Preparation onset to pelvic movement end (seconds).
9. Preparation onset to upward-ascent onset (seconds; missing if negative).
10. Extra absolute vertical-pelvis speed peaks: eligible peak count minus one,
    floored at zero (10% prominence; approximately 0.12-s minimum separation).

The seven legacy motion features retain their original filtering and automatic
5–95% feature window. Preparation uses pelvis OR relative-shoulder departure
from the initial 0.25-s baseline, sustained for 0.10 s, with fixed floors and
robust baseline-noise thresholds. The upward bout uses a separate 3-Hz velocity
anchor. The endpoint searches for a sustained low-velocity high-pelvis interval,
falling back to the legacy 95% crossing. These are exploratory operational
boundaries, not validated seat-off or fully upright events. Review is always
requested; no diagnosis, MDS-UPDRS score, or hand-support classification is produced.

## Results and manual review

The main graph shows normalized ankle-relative pelvis height. The preparation
panel shows pelvis and relative-shoulder departures divided by their thresholds;
1 denotes threshold crossing. Optional velocity is in image pixels/second,
with eligible peaks marked. All charts share real frame-based timestamps, event
markers and video seeking. Playback updates the chart cursor.

The small analysis window supports dragging or numerically editing preparation
onset, upward-ascent onset and pelvic movement end. Editing seeks the video;
**Apply boundaries** performs cached re-analysis. Ordered, finite, in-range
boundaries are required. Preparation-only edits change timing features, leaving
the motion window unchanged. An explicit rise-boundary edit uses the reviewed
rise interval for features 2–7 and 10, recomputing normalization at its end. The
10–90% ascent time remains a separately identified automatic measurement.
The current feature window and its provenance are shown below the plots.

**Restore automatic** recovers original boundaries and features. Saved project
JSON contains the complete pose cache, original automatic boundaries, applied
boundaries, feature window, camera inputs and height. Reloading the result
retains the ability to edit boundaries without detection.

`POST /api/update_sit_to_stand/` accepts multipart `json_data` with `task_data`
and `boundaries` (`preparation_start`, `rise_start`, `rise_end`) in absolute video
seconds, or `restore_automatic: true`. This task-specific path follows gait's
cached segment-editor pattern instead of applying repetitive-cycle tools to a
single rise. Display landmarks are not independently editable in this version;
landmark-role metadata makes that restriction explicit.

## Verification

Run `python manage.py check`, `python -m pytest tests/test_sit_to_stand.py`, and
the frontend `npm run build`. Focused tests cover timestamps, feature windows,
missing tracking, boundary errors, JSON reload/edit/restore, acquisition metadata,
route discovery and the task response without gait-phase inference. Broader
infrastructure, landmark editing and gait postprocessing tests protect shared
height/camera integration.

For manual acceptance: select Sit-to-stand; enter height and camera information;
analyze a complete frontal recording; inspect landmarks and all three boundaries;
apply a preparation edit and then a rise edit; save/reload project JSON; restore
automatic boundaries. Clinical validity still requires independently annotated
videos. This implementation does not carry study-specific participant exclusion
lists into the product.

Development verification on 2026-10-19: Django checks and frontend production
build passed; 62 focused backend tests passed across sit-to-stand, analysis
infrastructure, landmark editing, gait postprocessing and gait visibility. A
render smoke check covered the results plots and boundary controls. Comparison
against all 109 cached study trajectories reproduced available reference values
within numerical tolerance, including missing preparation lead-in values; see
`sit_to_stand_study_parity.json`. Three recordings have study-specific missing
legacy features and are not used as numerical references for those seven
features. This is not a fresh detector run or an independent clinical validation.
A fresh video/desktop interaction acceptance run remains to be performed.
