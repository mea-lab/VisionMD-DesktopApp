# Routine gait measures

- Step length: contacting-ankle displacement projected along straight-segment walking direction. Only this method is used; the pelvis-depth legacy estimator and duplicate SynthGait output aliases are removed.
- Gait speed: ankle-derived step length divided by step time, then equal-weight left/right means.
- Arm-swing amplitude: P95 minus P5 of pelvis-centred forward wrist displacement within each straight segment, normalized by leg length. Segment amplitude summaries are frame-weighted; sides are averaged equally.
- P95 speed: 95th percentile of absolute instantaneous speed, not a P5-to-P95 displacement range. Arm values include side values and their equal-side average.
- Trunk mediolateral measures: robust ROM (P95 minus P5 of pooled segment-local detrended displacement), mean absolute speed and P95 absolute speed. RMS displacement, duplicate displacement range and RMS velocity are removed from routine output.
- Turning: duration, camera-relative angle, mean angular speed and P95 absolute angular speed; peak angular speed is removed.
- Variability: one segment-first steady-step time SD and one segment-first steady-step width SD. Each side contributes sample variance within each segment, then sides and segments are combined with equal weight in variance space. See steady_step_gait.md.
- Diagnostics: untrimmed SDs, central-window length/speed SDs and asymmetries. Asymmetry currently uses absolute side differences before inference-pass averaging; mirror disagreement prevents treating it as validated clinical asymmetry.

Only new analyses and cached-boundary recalculation acquire the revised definitions. Original study outputs and fitted original classifier artifacts are preserved as research baselines; they are not silently relabeled as these new definitions.
