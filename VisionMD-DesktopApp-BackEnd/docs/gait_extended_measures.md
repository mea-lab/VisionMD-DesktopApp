# Extended gait measures

The existing MeTRAbs 17-joint gait skeleton and phase model are retained.
Reprocess a video or recompute its gait segments from cached poses/events to
obtain the new fields. Old exported numerical results are not retroactively
changed. FeatureTable automatically displays and exports result fields.

## Bilateral summaries

Pool valid observations across straight segments *within each side*, then use:

- Mean: `(mean_left + mean_right) / 2`.
- Variability: `sqrt((sample_variance_left + sample_variance_right) / 2)`.
- Asymmetry: `abs(mean_left - mean_right)`.

Both sides must have at least two samples for variability; otherwise NaN is
reported. Means/asymmetry require observations on both sides. These are raw
measurements, without the paper's statistical log/square-root transforms.

`Average step time` uses equal left/right weighting. Cadence is 60 / bilateral mean step time.
Temporal asymmetry/variability fields explicitly use ms; existing time means
remain seconds. Variability is marked estimated and frame interval is exposed.
Video-derived event timing, particularly toe-off timing, limits precision.
Subframe interpolation cannot establish accurate subframe event measurement.
Swing time, stance time, and double support time remain reported in seconds.
Swing/stance retain equal-L/R means, side-specific means, and asymmetry in ms.
Only their variability outputs are excluded. Incomplete phase intervals produce
unavailable duration outputs without preventing step metrics from being computed.
Double support retains the historical sum of its two component intervals.
No arbitrary FPS cutoff claims reliability.

Legacy `Average step length`, per-side legacy lengths, and `Average velocity`
retain their hip camera-depth definitions and existing aggregation. An additive
`L/R mean legacy step length` and `Legacy step length asymmetry` allow bilateral
comparison without overwriting historical definitions.

`SynthGait step length` and `Step width` now use bilateral means for new runs.
`SynthGait step velocity` is the bilateral mean of individual ankle-derived
step length / step time, not mean length / mean time. New analyses keep the
side of the landing ankle for every step. Existing spatial variability fields
use within-side variances rather than SD of pooled left/right steps; historic
sample sets without side labels retain their old spatial summaries. Step
length/width are in metres and step speed is m/s. Ankle positions approximate
heel-contact locations and require validation against reference measurements.

## Peak ankle lift

For each side, use a contact -> toe-off -> next-contact swing bracketed by
complete stances. The central halves of the two stance intervals provide
median ankle heights; interpolate a baseline between their mean frame times.
The peak ankle height above that baseline during the interior swing is one
observation. Output the mean of per-swing peaks per side and their bilateral
mean in mm, plus each side's valid swing count. Missing observations, incomplete
cycles, or negative peaks are excluded, not silently filled or clamped.

The reference is **camera vertical** (Y after the analyzer's existing sign flip).
Linear baseline drift is removed, but this is not calibrated ground-normal
distance, minimum toe clearance, or sole clearance. Camera pitch can attenuate
vertical lift. Supplied world-coordinate poses must follow the analyzer's
existing Y-down input convention; arbitrary extrinsics do not establish it.
A future floor-normal configuration should explicitly transform the analysis
frame rather than assume an extrinsic matrix establishes the correct axes.

## Arm and trunk velocities

Arm velocity is the derivative of wrist-minus-pelvis displacement projected
along the segment's walking axis, in m/s (not shoulder angular velocity).
Report mean absolute speed and the 95th percentile of absolute speed for each
side, with an equal-side summary. Signed means would cancel oscillatory motion;
P95 speed is explicitly a percentile, not an instantaneous peak.

Trunk velocity is the derivative of the existing detrended mediolateral
centroid displacement (pelvis/spine/neck). Report RMS velocity, mean absolute
speed, and P95 absolute speed. Existing displacement RMS and ROM are retained.

Derivatives use a local quadratic Savitzky–Golay fit over approximately 0.2 s,
with finite differences for short finite runs. Missing runs are not bridged.
Calculate each straight segment separately before pooling derivative samples;
never differentiate across a turn or discontinuity between segments. Filtering
reduces noise but can attenuate fast changes; this is a fixed documented
estimator, not a claim of clinical validation. FPS and landmark errors affect
all new outputs. Smoothing parameters should be versioned for cohort comparison.

Reference: Wilson et al. (2020), doi:10.3389/fnagi.2020.577435.

## Confirmed automatic turns

The standard gait task now confirms a turn using camera-depth reversal of the
MeTRAbs pelvis and a local shoulder/hip yaw change. Both a depth maximum (far
turn) and minimum (near turn) are considered. Each candidate needs at least one
second of approach and departure, opposing sustained trends within three
seconds on either side, and at least 100 mm of movement (or four times the
estimated depth noise). Depth is median-filtered over approximately 0.5 seconds;
feature landmarks remain unchanged.

Local yaw change must be 75–270 degrees. The exclusion interval uses its 5%–95%
crossings and must contain the depth reversal. If no candidate passes, the task
reports no confirmed turn and does not automatically exclude a fallback window.
The existing single-turn schema reports the strongest confirmed depth reversal.
Manual turn selection remains available. Turns without sufficient camera-depth
motion, multiple turns, and poorly estimated poses still require review. The
thresholds are conservative heuristics, not clinically validated cutoffs.
