# Batch analysis

Run this from `VisionMD-DesktopApp-BackEnd`. An invocation has one task and can
take one video or a folder of videos:

```bash
python batch_processing/batch_analyze.py /data/FT-right \
  --task finger_tap_right --weights /models/yolo11x-pose.pt \
  --output-dir /data/results/FT-right --device auto
```

`--device auto` is the default. It selects CUDA first, then Apple Metal (MPS),
then CPU. VisionMD enables PyTorch's native MPS CPU fallback and also retries a
whole model operation on CPU when PyTorch or a dependent library reports an
MPS/Metal operation as unsupported. After such a failure, new models stay on
CPU for the rest of the process instead of repeatedly failing. Use
`VISIONMD_TORCH_DEVICE=cpu` (or `--device cpu` in this batch tool) to disable
GPU inference explicitly.

Before localization or landmark inference, each input is copied into the
temporary batch workspace and normalized to a zero-based, constant-frame-rate
timeline. The source recording is never modified. Normalization preserves the
decoded frame count and aborts the video if FFmpeg and OpenCV do not agree,
preventing frame-indexed landmarks from drifting against browser playback.
FFmpeg and its matching FFprobe executable must be available on `PATH`.

For gait, also pass `--height-cm 175`. The static 5th--95th-percentile ROI is
derived with the supplied candidate-localization approach. Every stable
candidate is processed by VisionMD's existing task class. Candidates that fail
the task/pose pipeline are discarded; accepted candidates are ranked by signal
amplitude, peak count, and dominant-frequency feature.

Only the highest-ranked valid subject is exported. Candidate evaluation stays
internal; output filenames and the summary manifest contain no candidate list
or candidate-specific duplicates.

All task types shown by the desktop task selector are available, including
left/right pronation-supination and elbow-extended hand tremor. Use
`python batch_processing/batch_analyze.py --help` to see the exact task keys.

The batch writes one task-result JSON and one `*_visionmd_project.json` snapshot.
The snapshot can be selected directly with the desktop Home screen's **Load
Project JSON** action. The adjacent manifest records only the selected output
paths, completion status, and quality label.

## Signal and feature exports

The selected result also writes `*_signal.png` and `*_features.csv`.
The PNG overlays the same estimated technical quality label saved in
`analysisQuality`; multiple gait/tremor signals use separate panels. The
CSV has `feature,value` rows containing task/video, quality and reasons,
the original `radarTable` features, and top-level scalar gait/tremor features.
Feature names retain their original units; non-finite feature values become NA.
Landmarks, signals and internal caches remain in JSON, not the feature CSV.

The manifest records `signal_png`, `features_csv`, `result_json`,
`project_json`, and `analysis_quality` for each completed export. As with the
selected project, the highest-ranked accepted candidate also receives a PNG
and CSV without the candidate suffix. Ranking is a separate heuristic, not
the estimated technical quality label. A flat candidate can be discarded from
ranking while retaining its exported files. An inference failure has no result
to export; its exception is recorded in the manifest.

## Quality explanation

Click the Quality badge in Task Details to open a theme-aware dialog showing
the saved reasons, observed measurements, rules, and outcomes. The decision
algorithm is unchanged: fatal checks take precedence, then review warnings,
then Good. Only evaluated checks appear; early failures skip later checks.
P/S diagnostics and temporal-refinement acceptance are included when supplied.
These are technical checks, not a calibrated probability or clinical validity.

Older saved projects show their existing metrics/reasons, with an explicit
notice that detailed evidence was not recorded. New analyses and batch runs
save evidence alongside the quality label. No model rerun is performed by
opening the dialog. The generic screen uses the longest numeric signal, not
every gait/tremor channel; a Good label does not guarantee correctness.

Verification: `python -m pytest tests/test_batch_exports.py tests/test_analysis_infrastructure.py -q`
tests empty/flat/invalid/normal signals, P/S evidence, feature CSVs and PNGs
for ordinary, gait, and tremor result schemas without loading models.
