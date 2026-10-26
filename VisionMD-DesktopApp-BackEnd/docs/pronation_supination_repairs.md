# Pronation/supination tracking and angle repairs

P/S localization keeps the existing participant, handedness, coverage and gap checks. Duplicate boxes are suppressed before association. If both ordinary search passes fail, a bounded global association fallback uses observed detections anchored to the original partial participant track. Interpolated locations never count as detections; passing ordinary tracks remain unchanged.

Short angle-flip repairs now require adjacent large-jump boundaries. Pairing a farther exit across intervening jumps could turn a one-frame reconstruction outlier into an erroneous 180-degree shift of a complete movement.

The unrestricted temporal neural refiner is disabled. A pose-supported persistent 180/360-degree repair remains available. For unresolved excessive winding (central angle range above 250 degrees), one additional WiLoR run uses a stabilized crop with 0.8 times the fixed crop side. It must use the same angle estimator and agree with the initial movement. Only a single sustained 360-degree offset is supported. A transition of at most half a second can use independently inferred crop observations with endpoint offset matching. Other samples retain their waveform, allowing only the constant branch shift. Ambiguous cases retain the original result.

The cross-crop retry adds inference time only to unresolved excessive-range cases. Its diagnostics, reference quality, timing, original and final angles are returned in `psPipeline`. Repairs always require review; original quality failures are not silently promoted to passes. The cache version changes so existing P/S analysis caches are invalidated. Recompute an analysis to apply these changes; exported historical results are not rewritten.

## Validation

- Fresh GPU end-to-end analyses reproduced the winding correction and the short-flip correction on the two development cases.
- Replaying the saved raw landmark sequences from 20 manually annotated development videos left all 20 finalized angle traces unchanged, including the existing persistent branch repair.
- Replaying detector observations from 50 videos preserved all 46 previously passing crop trajectories exactly and recovered the other four under the original coverage/gap thresholds.
- Automated tests cover repair boundaries, preservation of observed motion, rejected cross-crop proposals, participant anchoring, unsupported detection gaps and cache invalidation.

These checks are development regression evidence, not held-out anatomical accuracy validation. The two difficult recordings still contain smaller local irregularities or terminal tracking problems. This change does not make every trace fully verified.
