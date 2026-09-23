# Batch analysis

Run this from `VisionMD-DesktopApp-BackEnd`. An invocation has one task and can
take one video or a folder of videos:

```bash
python batch_processing/batch_analyze.py /data/FT-right \
  --task finger_tap_right --weights /models/yolo11x-pose.pt \
  --output-dir /data/results/FT-right --device cuda
```

For gait, also pass `--height-cm 175`. The static 5th--95th-percentile ROI is
derived with the supplied candidate-localization approach. Every stable
candidate is processed by VisionMD's existing task class. Candidates that fail
the task/pose pipeline are discarded; accepted candidates are ranked by signal
amplitude, peak count, and dominant-frequency feature.

All task types shown by the desktop task selector are available, including
left/right pronation-supination and elbow-extended hand tremor. Use
`python batch_processing/batch_analyze.py --help` to see the exact task keys.

For every accepted candidate, the batch writes both a task-result JSON and a
`*_visionmd_project.json` snapshot. The snapshot can be selected directly with
the desktop Home screen's **Load Project JSON** action. A second snapshot
without a candidate suffix points to the highest-ranked accepted candidate.
The adjacent `*_manifest.json` records that selected snapshot, candidate
ranking, signal metrics, coverage, and discard reasons.
