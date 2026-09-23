# Performance and analysis jobs

## Frontend

- Task-selection and task-result modules are loaded on demand. Plotly remains
  in a separate lazy chunk, reducing the initial renderer bundle from roughly
  15.4 MB to 1.21 MB.
- Analysis uploads contain parameters only; videos stay in the project store
  and are no longer copied through the renderer for each request.
- Auto Process and Analyze All use the background job API. The UI distinguishes
  queued and running work. A queued job can be cancelled; a running GPU kernel
  is allowed to finish because forcibly killing it can invalidate CUDA state.

## Backend

- `app/views/analysis_jobs.py`: one-worker inference queue and status API.
- `app/analysis/analysis_cache.py`: parameter/video-aware result cache.
- `app/analysis/model_registry.py`: process-local model-weight reuse. YOLO
  predictor state is reset for every video.
- `app/analysis/analysis_quality.py`: conservative technical quality metadata.
- Task responses include total/stage timing where supported.

The process-local queue fits the packaged desktop application, which runs one
Django backend process. A future multi-process/server deployment should replace
it with a durable queue (for example Redis/Celery) and persistent job records.

## P/S fast screen

`ps_method=auto` first attempts MediaPipe world landmarks. It is not a casual
preview: strict gates decide whether it is usable, and even an accepted output
is marked provisional/requires verification. Rejected screens fall through to
YOLO + WiLoR in the same job. `ps_method=wilor` skips the screen.

## Batch compatibility

Batch output contains per-task JSON, a manifest, and importable VisionMD project
snapshots. Hand Movement defaults to palm-size normalization; all other tasks
retain their task-specific/default normalization. Candidate-specific snapshots
are preserved and the highest-ranked accepted candidate is also exported as the
video's best project snapshot.
