# Estimated step width

`Step width` uses opposite-foot progression-line geometry. For R-L-R contacts, calculate the middle left ankle’s perpendicular distance to the line through the surrounding right ankle contacts, and conversely for L-R-L. Units are metres. This approximates heel-based walkway geometry using ankle landmarks in the estimated camera-XZ plane. Invalid or degenerate triplets do not contribute a width, with no fallback to the former segment-axis definition.

The width mean combines side means equally. Report only `Steady-step width within-segment SD (m; estimated)` for width variability, following the two-second central windows and equal-side/equal-segment variance pooling in steady_step_gait.md. Pooled-all-step width SD remains diagnostic metadata for audit, not a second routine estimate. Both inference passes must meet the reporting minimum; no substitution of untrimmed observations.

The paper’s pooled-side SD and this segment-first SD have different aggregation definitions. Better numerical agreement does not establish equivalence of ankle and heel measurements. Source: Wilson et al., Frontiers in Aging Neuroscience 12:577435; GAITRite geometry illustration https://www.nature.com/articles/s41598-023-32948-z#Fig1.
