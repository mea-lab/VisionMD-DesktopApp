# Hand-task normalization defaults

Finger tapping defaults to INDEXSIZE; hand movement defaults to PALMSIZE. The interface and batch CLI use these defaults. Left/right hand-movement backend instances and omitted/empty request settings also use PALMSIZE. Explicit overrides remain supported. Switching task types chooses the new task default; same-type edits preserve explicit selections and manual regions.

INDEXSIZE is the index MCP–PIP–DIP–tip chain length. PALMSIZE is the mean wrist-to-index/middle/ring/pinky MCP distance. The maximum across the task window is the normalization factor. Amplitudes are normalized displacement, speeds normalized displacement per second, timing seconds, frequency Hz, CV fractions and decay early/late ratios.

A changed task setting does not retroactively change saved results. A fixed-cycle normalization conversion multiplies amplitude/speed means and SDs and signals by old_factor/new_factor, preserving selected cycles, timing, CVs and ratios. Rerunning cycle detection can change these quantities and is a different procedure. Confirm historical scales from saved factors and landmarks rather than metric names.


### Manual landmark edits

Dragging a displayed FT or HM point now updates its corresponding full-hand XY coordinates (depth is retained), then recalculates normalization using the task-selected strategy. Edited coordinates and the strategy persist in the analysis cache/results so subrange re-analysis preserves the correction. FT defaults to INDEXSIZE and HM to PALMSIZE when no explicit strategy is supplied.

A manual displacement larger than one estimated palm length may place a corrected point beside joints from a different detected hand. Such frames remain in the edited signal but are excluded from normalization, recorded in normalizationQuality and analysis_cache.normalization_excluded_frames, and marked for review. This is a heuristic safeguard, not a full correction of the other joints. Normalization still uses the existing maximum across eligible frames. No video orientation changes are involved.


### Brief fingertip identity failures

Finger-tapping analysis checks the thumb separately from the four other fingertips. Thumb/index contact is valid; thumb correction requires an abrupt hand-relative excursion plus inconsistent distal-bone geometry or a thumb-MCP branch spike while the other MCPs and wrist remain sufficiently stable. Only short bounded runs (default up to 0.12 seconds) are interpolated from surrounding accepted points. Whole-thumb branch errors update the related thumb joints consistently. Sustained and edge failures are left visible and flagged for review. The checks do not smooth accepted landmarks and are heuristic, not a guarantee of anatomical correctness.

The original 001-057 Visit4 right FT saved landmarks flagged thumb frames 34, 52, 72 and 95 (zero based); the latest manually corrected project thumb coordinates were unchanged by the thumb check. Synthetic tests cover brief/sustained swaps, true thumb/index contact, smooth tapping, hand translation and rapid hand repositioning. Previously saved results are not silently rerun through the new detector; user-corrected projects remain the analysis inputs.
