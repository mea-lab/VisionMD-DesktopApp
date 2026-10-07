# Landmark roles

VisionMD persists a `landmarkSchema` object with each task result. It identifies
landmark arrays by purpose instead of assuming that every array named
`landMarks` is both the video overlay and the analysis input.

## Roles

- `display` names the array rendered over the source video. Its coordinates are
  video pixels.
- `analysis` names the array that produced the task signal and measurements.
- `normalization` names the landmarks or calibration data used to convert the
  signal to normalized or physical units.
- `orientation`, when present, names a separate track used only to determine
  walking direction or turns.
- `manualEditing.supported` states whether moving a displayed 2D point can be
  propagated safely through analysis.

The schema stores keys rather than copies of landmark arrays. Existing JSON
files without this metadata remain readable: the desktop app treats
`landMarks` as the display and analysis array, and only enables editing for the
legacy tasks whose analysis is based directly on those 2D points.

## Task-specific behavior

| Task | Display | Analysis | Editing |
| --- | --- | --- | --- |
| Gait | corrected 2D `landMarks` | corrected 3D `landMarks_3D` | disabled because a 2D edit cannot update 3D consistently |
| Finger tap, hand movement, leg agility, toe tapping | `landMarks` | `landMarks` | enabled |
| Hand pronation/supination | XY portion of `landMarks` | stored 3D orientation angle | disabled |
| Hand tremor | displayed joint subset | full repaired detector track, not persisted | disabled |

For gait, left/right swaps detected from the 3D continuity check are applied to
the 2D display track using the same frame-level swap mask. The original 3D
orientation track remains in `gait_analysis_cache.poses3d_orientation` because
turn detection must run before continuity-based identity correction. The result
also reports the number of corrected frames under
`quality.landmark_identity`.
