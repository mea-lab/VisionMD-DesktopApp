from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from app.analysis.analysis_quality import assess_analysis_quality
from app.analysis.landmark_schema import attach_landmark_schema
import importlib
import json
import copy
import math


HAND_DISPLAY_INDICES = {
    "Finger Tap Left": (4, 8),
    "Finger Tap Right": (4, 8),
    "Hand Movement Left": (8, 12, 16, 0),
    "Hand Movement Right": (8, 12, 16, 0),
}


def synchronize_hand_landmarks(task_name, display_frames, full_frames):
    """Apply edited XY coordinates to the matching full hand landmarks.

    A fingertip moved more than a palm length can belong to a different
    detected hand. Its unedited joints cannot provide a trustworthy scale;
    retain that frame for the edited signal but exclude it from normalization.
    """
    indices = HAND_DISPLAY_INDICES.get(task_name)
    corrected = copy.deepcopy(full_frames)
    excluded = []
    if indices is None:
        return corrected, excluded
    for i, (display, full) in enumerate(zip(display_frames, corrected)):
        if len(display) != len(indices) or len(full) != 21:
            continue
        palm = sum(math.dist(full[0][:2], full[j][:2]) for j in (5, 9, 13, 17)) / 4
        for point, index in zip(display, indices):
            displacement = math.dist(point[:2], full[index][:2])
            if displacement > max(palm, 1.0):
                excluded.append(i)
            full[index][:2] = point[:2]
    return corrected, sorted(set(excluded))


@api_view(['POST'])
def update_landmarks(request):
    """
    Given a JSON payload containing:
      - 'task_name'
      - 'landmarks' (i.e. display_landmarks)
      - 'fps', 'start_time', 'end_time'
      - 'allLandMarks'
      - 'normalization_factor'
    Re-run the final step of analysis (peak finding, stats, etc.)
    using the new pipeline structure.
    """
    try:
        json_data = json.loads(request.POST['json_data'])
    except (KeyError, json.JSONDecodeError):
        raise Http404("Invalid or missing 'json_data' in POST body")

    # Extract fields
    task_name = json_data.get('task_name')
    requested_start_time = float(json_data.get('start_time', 0))
    requested_end_time = float(json_data.get('end_time', 0))
    fps = float(json_data.get('fps', 0))

    # ``analysis_cache`` is the landmark sequence produced by the original
    # detector run.  Re-analysis may select any subrange of this sequence, but
    # must never claim to support frames outside it: those would need a new
    # landmark-detection pass over the video.
    cache = json_data.get('analysis_cache') or {}
    cache_start_time = float(cache.get('start_time', requested_start_time))
    cache_end_time = float(cache.get('end_time', requested_end_time))
    cached_essential_landmarks = cache.get('landMarks', json_data.get('landmarks', []))
    cached_all_landmarks = cache.get('allLandMarks', json_data.get('allLandMarks', []))
    cache_start_frame = int(cache.get('landmark_start_frame', 0))
    normalization_excluded_frames = set(cache.get('normalization_excluded_frames', []))

    if fps <= 0:
        raise ValueError('A positive fps value is required for cached re-analysis.')
    if requested_end_time <= requested_start_time:
        raise ValueError('Analysis end time must be greater than start time.')
    if requested_start_time < cache_start_time or requested_end_time > cache_end_time:
        raise ValueError(
            f'Requested analysis range {requested_start_time:.3f}-{requested_end_time:.3f}s '
            f'is outside the cached landmark range {cache_start_time:.3f}-{cache_end_time:.3f}s.'
        )

    start_index = max(0, round((requested_start_time - cache_start_time) * fps))
    end_index = min(len(cached_essential_landmarks), round((requested_end_time - cache_start_time) * fps))
    if json_data.get('persist_landmark_edits') is True:
        submitted_landmarks = json_data.get('landmarks')
        expected_frames = end_index - start_index
        if not isinstance(submitted_landmarks, list):
            raise ValueError('Manual landmark edits must include a landmarks array.')
        if len(submitted_landmarks) != expected_frames:
            raise ValueError(
                f'Manual landmark edit contains {len(submitted_landmarks)} frames; '
                f'the selected range contains {expected_frames}.'
            )
        edited_full_landmarks, excluded_frames = synchronize_hand_landmarks(
            task_name, submitted_landmarks, cached_all_landmarks[start_index:end_index]
        )
        cached_all_landmarks = list(cached_all_landmarks)
        cached_all_landmarks[start_index:end_index] = edited_full_landmarks
        normalization_excluded_frames.update(start_index + i for i in excluded_frames)
        cached_essential_landmarks = list(cached_essential_landmarks)
        cached_essential_landmarks[start_index:end_index] = submitted_landmarks

    essential_landmarks = cached_essential_landmarks[start_index:end_index]
    all_landmarks = cached_all_landmarks[start_index:end_index]
    if len(essential_landmarks) < 2 or len(all_landmarks) < 2:
        raise ValueError('The selected range contains too few cached landmark frames.')

    # 1) Get the Task
    file_name = task_name.lower().replace(" ", "_")
    class_name = task_name.title().replace(" ", "") + "Task"
    module_path = f"app.analysis.tasks.{file_name}"

    try:
        task_module = importlib.import_module(module_path)
    except ModuleNotFoundError:
        raise Http404(f"Couldn’t find task module '{module_path}'")

    try:
        TaskClass = getattr(task_module, class_name)
    except AttributeError:
        raise Http404(f"Module '{module_path}' has no class '{class_name}'")

    try:
        task = TaskClass()
        task.task_norm_strategy = (json_data.get('norm_strategy')
                                   or json_data.get('normalization_strategy')
                                   or task.task_norm_strategy or 'INDEXSIZE')
        raw_signal = task.calculate_signal(essential_landmarks)
        signal_analyzer = task.get_signal_analyzer()
        normalization_landmarks = [
            frame for i, frame in enumerate(all_landmarks)
            if start_index + i not in normalization_excluded_frames
        ]
        if not any(normalization_landmarks):
            raise ValueError('No trustworthy full landmark frames remain for normalization.')
        normalization_factor = task.calculate_normalization_factor(normalization_landmarks)
        output = signal_analyzer.analyze(
            normalization_factor=normalization_factor,
            raw_signal=raw_signal,
            start_time=requested_start_time,
            end_time=requested_end_time
        )

        output["landMarks"] = essential_landmarks
        output["allLandMarks"] = all_landmarks
        output["normalization_factor"] = normalization_factor
        output["normalization_strategy"] = task.task_norm_strategy
        output["normalizationQuality"] = {
            "excluded_frame_count": sum(start_index <= i < end_index for i in normalization_excluded_frames),
            "reason": "Large manual landmark displacement; unedited full-hand joints may belong to another hand.",
        }
        output["landmark_start_frame"] = cache_start_frame + start_index
        output["landmark_fps"] = fps
        if isinstance(json_data.get("landmarkQuality"), dict):
            output["landmarkQuality"] = json_data["landmarkQuality"]
        # Preserve the complete detector output for later subrange changes.
        output["analysis_cache"] = {
            "start_time": cache_start_time,
            "end_time": cache_end_time,
            "fps": fps,
            "landMarks": cached_essential_landmarks,
            "allLandMarks": cached_all_landmarks,
            "landmark_start_frame": cache_start_frame,
            "normalization_excluded_frames": sorted(normalization_excluded_frames),
        }
        output["analysisQuality"] = assess_analysis_quality(output)
        attach_landmark_schema(output, file_name)
        if output["normalizationQuality"]["excluded_frame_count"]:
            quality = output["analysisQuality"]
            quality.setdefault("reasons", []).append(
                "Normalization excludes frames with large manual edits; review full-hand tracking."
            )
            if quality.get("status") != "failed":
                quality.update(status="review", label="Needs review")
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(output)
