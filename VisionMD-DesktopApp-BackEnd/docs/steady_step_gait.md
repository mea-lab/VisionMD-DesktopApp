# Steady-step gait and variability

Report one SD per measure: `Steady-step gait time SD (ms)` and `Steady-step width within-segment SD (m; estimated)`.

Exclude two seconds at the beginning and end of every accepted straight-walking segment. Both temporal contact endpoints, and all three bracketing width contacts, must be inside the central interval. Within segment j calculate sample variances separately by side, using n-1 degrees of freedom:

`segment_variance_j = (variance_left_j + variance_right_j) / 2`

Then combine segments with equal weight:

`combined_SD = sqrt(mean(segment_variance_j))`

This is RMS pooling of segment SDs, not their arithmetic mean. It excludes changes between segment means and does not weight longer segments more heavily. Both sides need at least two samples for a segment to contribute. Across valid segments each side needs at least five contributing samples in each inference pass. Average the original and mirrored pass SDs only when both are available; otherwise display `Not available: insufficient steady steps`. Zero SD is valid for a constant trace. Metadata preserves segment SDs, segment counts, sample counts and availability.

Use this hierarchy for every variability estimate. Step-length and step-speed SD are retained in diagnostic metadata, including estimates on the same central windows, because depth/pose uncertainty remains substantial. Untrimmed SD and asymmetry estimates are also diagnostic; they are not routine-report metrics. Swing-time, stance-time and double-support variability are not calculated for reporting.

The paper pools left/right observations across passes; segment-first pooling is a deliberate definition difference. Central windows operationally define steady-step gait, without independently proving constant speed or validating event timing. Existing saved results require recalculation.
