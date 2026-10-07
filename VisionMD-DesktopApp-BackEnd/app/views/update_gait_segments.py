import json

import numpy as np
from rest_framework.decorators import api_view
from rest_framework.response import Response

from app.analysis.tasks.gait import GaitTask
from app.analysis.signal_analyzers.gait_reporting import public_features


@api_view(["POST"])
def update_gait_segments(request):
    """Recalculate gait results after editing the walking/turn boundaries.

    The initial gait response stores the MeTRAbs poses and gait-transformer
    outputs in ``gait_analysis_cache``.  This endpoint works exclusively from
    that cache: changing a turn interval never decodes the video or estimates
    landmarks again.
    """
    try:
        payload = json.loads(request.POST["json_data"])
        task_data = payload["task_data"]
        cache = task_data["gait_analysis_cache"]

        fps = float(cache["fps"])
        start_time = float(cache["start_time"])
        start_frame_idx = int(cache.get("start_frame_idx", round(start_time * fps)))
        poses = np.asarray(cache["poses3d"], dtype=float)
        orientation_poses = np.asarray(cache["poses3d_orientation"], dtype=float)
        poses_mirrored = np.asarray(cache["poses3d_mirrored"], dtype=float)
        phases = np.asarray(cache["phases"], dtype=float)
        strides = np.asarray(cache["strides"], dtype=float)
        phases_mirrored = np.asarray(cache["phases_mirrored"], dtype=float)
        strides_mirrored = np.asarray(cache["strides_mirrored"], dtype=float)

        arrays = (
            poses, orientation_poses, poses_mirrored, phases, strides,
            phases_mirrored, strides_mirrored,
        )
        frame_count = len(poses)
        if fps <= 0 or frame_count < 2 or any(len(item) != frame_count for item in arrays):
            raise ValueError("The cached gait arrays are incomplete or inconsistent.")

        task = GaitTask()
        task.fps = fps
        task.start_time = start_time
        task.start_frame_idx = start_frame_idx
        spatial_calibration = cache.get("spatial_calibration")

        selected = payload.get("turning_segment") or {}
        if bool(selected.get("is_turning")):
            selected_start = float(selected["start_time_seconds"])
            selected_end = float(selected["end_time_seconds"])
            cache_end = start_time + (frame_count - 1) / fps
            if selected_start < start_time or selected_end > cache_end or selected_end <= selected_start:
                raise ValueError(
                    f"Turn interval must be inside {start_time:.3f}-{cache_end:.3f} seconds."
                )
            turn_start = int(round((selected_start - start_time) * fps))
            turn_end = int(round((selected_end - start_time) * fps))
            turning_metadata = task.measure_turn_range(
                orientation_poses, turn_start, turn_end
            )
        else:
            # A deliberately unreachable automatic threshold gives us the
            # canonical no-turn metadata without duplicating its schema.
            turning_metadata = task.detect_turn(
                orientation_poses, minimum_turn_degrees=float("inf")
            )

        analyzer = task.get_signal_analyzer()
        analysis = task.analyze_straight_walking_segments(
            analyzer,
            phases,
            strides,
            poses,
            phases_mirrored,
            strides_mirrored,
            poses_mirrored,
            turning_metadata,
            spatial_calibration=spatial_calibration,
        )
        averages = task.calculate_average_features(
            analysis["results"], analysis["results_mirrored"]
        )
        gait_events = analysis["gait_event_dic"]

        output = public_features(task_data)
        output.update(averages)
        output["gait_event_dic"] = {
            key: value.tolist() for key, value in gait_events.items()
        }
        output["gait_event_dic_mirrored"] = {
            key: value.tolist()
            for key, value in analysis["gait_event_dic_mirrored"].items()
        }
        output["landmark_colors"] = task.calculate_landmark_colors(
            poses, gait_events, fps
        ).tolist()
        output["turning_metadata"] = turning_metadata
        output["segment_metrics"] = analysis["segment_metrics"]
        output["gait_quality"] = {
            **analysis["quality"],
            "manual_segment_override": True,
        }
        return Response(output)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return Response({"detail": str(exc)}, status=400)
    except Exception as exc:
        return Response({"detail": f"Could not recalculate gait segments: {exc}"}, status=500)
