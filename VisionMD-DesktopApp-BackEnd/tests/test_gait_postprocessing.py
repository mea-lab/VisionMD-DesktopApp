import numpy as np
import json
from rest_framework.test import APIRequestFactory

from app.analysis.signal_analyzers.gait_signal_analyzer import GaitSignalAnalyzer
from app.analysis.signal_analyzers.gait_spatial_calibration import (
    HEIGHT_CALIBRATION_COEFFICIENT,
    height_spatial_calibration,
)
from app.analysis.tasks.base_task import BaseTask
from app.analysis.tasks.gait import GaitTask
from app.views.update_gait_segments import update_gait_segments


def test_landmark_repair_fills_spike_but_preserves_observations():
    frames = []
    for frame in range(20):
        x = frame * 0.01
        frames.append([[x, 0.0], [x, 1.0], [x + 1.0, 0.0]])
    frames[10][0] = [10.0, 10.0]

    repaired, quality = BaseTask.repair_landmark_track(frames, fps=30, return_quality=True)
    repaired = np.asarray(repaired)

    assert quality["rejected_outlier_count"] == 1
    assert np.allclose(repaired[5], np.asarray(frames[5]))
    assert np.linalg.norm(repaired[10, 0] - np.array([0.1, 0.0])) < 0.1


def test_landmark_gap_filling_does_not_smooth_valid_samples():
    frames = [[[0.0, 0.0]], [[1.0, 1.0]], [], [[3.0, 9.0]], [[4.0, 16.0]]]
    repaired, quality = BaseTask.repair_landmark_track(
        frames, reject_outliers=False, return_quality=True
    )
    repaired = np.asarray(repaired)

    assert quality["missing_frame_count"] == 1
    assert np.array_equal(repaired[[0, 1, 3, 4], 0], np.array([[0, 0], [1, 1], [3, 9], [4, 16]]))
    assert np.all(np.isfinite(repaired))


def test_turn_metadata_reports_angular_duration_and_absolute_frames():
    fps = 30.0
    frame_count = 180
    yaw = np.concatenate([
        np.zeros(45),
        np.linspace(0.0, np.pi, 90),
        np.full(45, np.pi),
    ])
    poses = np.zeros((frame_count, 17, 3), dtype=float)
    axis = np.column_stack([np.cos(yaw), np.zeros(frame_count), np.sin(yaw)])
    # Directed right-to-left hip/shoulder axes.
    for right, left in ((8, 11), (2, 5)):
        poses[:, right] = axis * 0.5
        poses[:, left] = -axis * 0.5

    # Camera-depth reversal must corroborate the body orientation change.
    poses[:, :, 2] += (3000 + 1000*np.sin(np.linspace(0, np.pi, frame_count)))[:, None]

    task = GaitTask()
    task.fps = fps
    task.start_frame_idx = 100
    task.start_time = 100 / fps
    metadata = task.detect_turn(poses)

    assert metadata["is_turning"] is True
    assert 150 < abs(metadata["angle_degrees"]) < 190
    assert metadata["start_video_frame"] == 100 + metadata["start_frame"]
    assert metadata["end_video_frame"] == 100 + metadata["end_frame"]
    assert metadata["duration_seconds"] > 0
    assert metadata["p95_angular_speed_degrees_per_second"] > 0


def test_feature_pooling_uses_event_counts_not_segment_counts():
    def samples(step_times):
        values = np.asarray(step_times, dtype=float)
        return {
            "stance_left": values,
            "stance_right": values,
            "swing_left": values,
            "swing_right": values,
            "step_time_left": values,
            "step_time_right": values,
            "double_support": values,
            "step_length_left": values,
            "step_length_right": values,
            "velocity": np.asarray([values.mean()]),
            "velocity_weight": np.asarray([len(values)]),
            "arm_correlation": np.asarray([values.mean()]),
            "arm_correlation_weight": np.asarray([len(values)]),
        }

    pooled = GaitSignalAnalyzer.pool_feature_samples([
        samples([1.0] * 10),
        samples([3.0] * 2),
    ])

    expected = (10.0 + 6.0) / 12.0
    assert np.isclose(pooled["Average step time"], expected)
    assert not np.isclose(pooled["Average step time"], 2.0)


def test_height_spatial_calibration_uses_median_head_to_ankle_stature():
    poses = np.zeros((5, 17, 3), dtype=float)
    poses[:, 0, 1] = np.asarray([1700, 1700, 1700, 1700, 2500], dtype=float)

    calibration = height_spatial_calibration(poses, height_cm=170)

    assert np.isclose(calibration["model_straight_stature_m"], 1.7)
    assert np.isclose(calibration["scale_factor"], HEIGHT_CALIBRATION_COEFFICIENT)
    assert calibration["source_pose_pass"] == "original"
    assert calibration["applied_to"] == ["step_length", "step_speed"]


def test_straight_segment_analysis_applies_one_scale_to_both_pose_passes():
    class StubAnalyzer:
        @staticmethod
        def analyze(
            phases, strides, poses, fps, return_details=False, spatial_scale=1.0
        ):
            events = {
                "left_down": np.asarray([10.0, 40.0]),
                "left_up": np.asarray([20.0, 50.0]),
                "right_down": np.asarray([25.0, 55.0]),
                "right_up": np.asarray([35.0, 65.0]),
            }
            samples = {
                "step_time_left": np.asarray([0.5, 0.5]),
                "step_time_right": np.asarray([0.5, 0.5]),
                "synthgait_step_length": np.asarray([0.5, 0.7]),
                "synthgait_step_length_left": np.asarray([0.5]),
                "synthgait_step_length_right": np.asarray([0.7]),
                "step_speed": np.asarray([1.0, 1.4]),
                "step_speed_left": np.asarray([1.0]),
                "step_speed_right": np.asarray([1.4]),
                "arm_correlation": np.asarray([0.0]),
                "arm_correlation_weight": np.asarray([len(poses)]),
            }
            for key in tuple(samples):
                if key.startswith("synthgait_step_length") or key.startswith("step_speed"):
                    samples[key] = samples[key] * spatial_scale
            result = GaitSignalAnalyzer.pool_feature_samples([samples])
            return result, events, samples, {"used_cleaned_events": True}

        pool_feature_samples = staticmethod(GaitSignalAnalyzer.pool_feature_samples)

    task = GaitTask()
    task.fps = 30.0
    task.start_frame_idx = 0
    poses = np.zeros((90, 17, 3), dtype=float)
    poses[:, 14, 2] = np.arange(90) * 10.0
    calibration = {"version": "test", "scale_factor": 0.8}

    analysis = task.analyze_straight_walking_segments(
        StubAnalyzer(),
        np.zeros((90, 8)),
        np.zeros((90, 9)),
        poses,
        np.zeros((90, 8)),
        np.zeros((90, 9)),
        poses.copy(),
        {"is_turning": False},
        spatial_calibration=calibration,
    )

    assert np.isclose(analysis["results"]["Average step length"], 0.48)
    assert np.isclose(analysis["results"]["Average velocity"], 0.96)
    assert np.isclose(analysis["results_mirrored"]["Average step length"], 0.48)
    assert np.isclose(analysis["results"]["Average step time"], 0.5)
    assert analysis["quality"]["spatial_calibration"] == calibration


def test_turn_interval_is_excluded_and_event_frames_are_restored():
    class StubAnalyzer:
        @staticmethod
        def analyze(
            phases, strides, poses, fps, return_details=False, spatial_scale=1.0
        ):
            count = len(poses)
            events = {
                "left_down": np.asarray([5.0, 25.0]),
                "left_up": np.asarray([12.0, 32.0]),
                "right_down": np.asarray([15.0, 35.0]),
                "right_up": np.asarray([22.0, 42.0]),
            }
            value = np.asarray([count / 30.0, count / 30.0])
            samples = {
                "stance_left": value,
                "stance_right": value,
                "swing_left": value,
                "swing_right": value,
                "step_time_left": value,
                "step_time_right": value,
                "double_support": value,
                "step_length_left": value,
                "step_length_right": value,
                "velocity": np.asarray([1.0]),
                "velocity_weight": np.asarray([count]),
                "arm_correlation": np.asarray([0.0]),
                "arm_correlation_weight": np.asarray([count]),
            }
            result = GaitSignalAnalyzer.pool_feature_samples([samples])
            quality = {"used_cleaned_events": True}
            return result, events, samples, quality

        pool_feature_samples = staticmethod(GaitSignalAnalyzer.pool_feature_samples)

    frame_count = 180
    poses = np.zeros((frame_count, 17, 3), dtype=float)
    poses[:, 14, 2] = np.arange(frame_count)
    phases = np.zeros((frame_count, 8), dtype=float)
    strides = np.zeros((frame_count, 9), dtype=float)
    task = GaitTask()
    task.fps = 30.0
    task.start_frame_idx = 0
    turn = {"is_turning": True, "start_frame": 60, "end_frame": 120}

    analysis = task.analyze_straight_walking_segments(
        StubAnalyzer(), phases, strides, poses, phases, strides, poses, turn
    )

    all_events = np.concatenate(list(analysis["gait_event_dic"].values()))
    assert np.all((all_events < 60) | (all_events > 120))
    assert len(analysis["segment_metrics"]) == 2
    assert analysis["quality"]["turn_excluded_from_primary_results"] is True


def test_step_cleaner_trims_only_low_progress_boundary_event():
    analyzer = GaitSignalAnalyzer()
    order = np.array([
        analyzer._metrabs_joint_order.tolist().index(name)
        for name in analyzer._gait_phase_joint_order
    ])
    poses = np.zeros((80, 17, 3), dtype=float)
    strike_frames = np.array([2, 18, 33, 48, 64])
    # Millimetres: the first interval advances only 5 mm, while a similarly
    # short interior interval is deliberately retained.
    strike_depth = np.array([0, 5, 300, 310, 600], dtype=float)
    poses[:, 14, 2] = np.interp(np.arange(80), strike_frames, strike_depth)
    events = {
        "left_down": np.array([2.0, 33.0, 64.0]),
        "right_down": np.array([18.0, 48.0]),
        "left_up": np.array([10.0, 40.0, 70.0]),
        "right_up": np.array([25.0, 55.0]),
    }

    cleaned, quality = analyzer.clean_gait_events(events, poses, order, fps=30.0)

    assert cleaned["left_down"].tolist() == [33.0, 64.0]
    assert cleaned["right_down"].tolist() == [18.0, 48.0]
    assert quality["rejected_boundary_heel_strikes"] == 1
    assert quality["boundary_progress_threshold_m"] >= 0.01


def test_synthgait_spatial_features_match_forward_lateral_definitions():
    analyzer = GaitSignalAnalyzer()
    frame_count = 100
    poses = np.zeros((frame_count, 17, 3), dtype=float)
    index = {name: i for i, name in enumerate(analyzer._metrabs_joint_order)}
    # Millimetres. The subject advances 1 cm per frame along camera Z.
    pelvis_z = np.arange(frame_count) * 10.0
    for name in analyzer._metrabs_joint_order:
        poses[:, index[name], 2] = pelvis_z
    poses[:, index["neck"], 1] = 600.0
    poses[:, index["neck"], 2] += 100.0  # 10 cm forward neck offset
    poses[:, index["spin"], 1] = 300.0
    # Both legs are 0.8 m long: hip->knee and knee->ankle are 0.4 m.
    for side, hip, knee, ankle, x in (
        ("right", "rhip", "rkne", "rank", -100.0),
        ("left", "lhip", "lkne", "lank", 100.0),
    ):
        poses[:, index[hip], 0] = x
        poses[:, index[hip], 1] = 0.0
        poses[:, index[knee], 0] = x
        poses[:, index[knee], 1] = -400.0
        poses[:, index[ankle], 0] = x
        poses[:, index[ankle], 1] = -800.0
    # Pelvis-centred wrists each sweep 20 cm in the walking direction.
    wrist_sweep = 100.0 * np.sin(np.linspace(0, 2 * np.pi, frame_count))
    poses[:, index["rwri"], 2] += wrist_sweep
    poses[:, index["lwri"], 2] -= wrist_sweep

    features = analyzer._synthgait_spatial_features(
        poses[:, [index[name] for name in analyzer._gait_phase_joint_order]] / 1000.0,
        np.array([10, 30, 50, 70]),
        np.array([20, 40, 60, 80]),
    )

    assert np.allclose(features["step_widths"], 0.2)
    assert np.allclose(features["step_lengths"], 0.1)
    assert np.isclose(features["stooped_posture"], 0.125)
    assert np.isclose(features["left_arm_swing"], 0.25, atol=0.005)
    assert np.isclose(features["right_arm_swing"], 0.25, atol=0.005)
    assert np.isclose(features["arm_swing"], 0.25, atol=0.005)
    assert np.isclose(features["arm_swing_correlation"], -1.0, atol=1e-6)
    assert np.allclose(features["step_speeds"], 0.3)
    assert features["torso_ml_rms"] < 1e-9


def test_spatial_scale_changes_length_and_speed_without_changing_width_or_timing():
    analyzer = GaitSignalAnalyzer()
    index = {name: i for i, name in enumerate(analyzer._metrabs_joint_order)}
    order = np.asarray([index[name] for name in analyzer._gait_phase_joint_order])
    poses = np.zeros((100, 17, 3), dtype=float)
    poses[:, :, 2] = (np.arange(100) * 10.0)[:, None]
    poses[:, index["rank"], 0] = -100.0
    poses[:, index["lank"], 0] = 100.0
    events = {
        "left_down": np.asarray([10.0, 30.0, 50.0, 70.0]),
        "left_up": np.asarray([25.0, 45.0, 65.0, 85.0]),
        "right_down": np.asarray([20.0, 40.0, 60.0, 80.0]),
        "right_up": np.asarray([15.0, 35.0, 55.0, 75.0]),
    }

    raw = analyzer.analyze_gait_video_features(events, poses, order, fps=30.0)
    scaled = analyzer.analyze_gait_video_features(
        events, poses, order, fps=30.0, spatial_scale=0.8
    )

    assert np.isclose(scaled["Average step length"], raw["Average step length"] * 0.8)
    assert np.isclose(scaled["Average velocity"], raw["Average velocity"] * 0.8)
    assert np.isclose(scaled["Step width"], raw["Step width"])
    assert np.isclose(scaled["Average step time"], raw["Average step time"])


def test_boundary_step_filter_discards_outer_steps_when_possible():
    analyzer = GaitSignalAnalyzer()
    events = {
        "left_down": np.asarray([10.0, 30.0, 50.0]),
        "right_down": np.asarray([20.0, 40.0, 60.0]),
        "left_up": np.asarray([15.0, 35.0, 55.0]),
        "right_up": np.asarray([25.0, 45.0, 65.0]),
    }

    filtered, quality = analyzer.discard_boundary_steps(events)

    assert quality["boundary_steps_discarded"] is True
    assert filtered["left_down"].tolist() == [30.0, 50.0]
    assert filtered["right_down"].tolist() == [20.0, 40.0]
    assert np.array_equal(filtered["left_up"], events["left_up"])
    assert np.array_equal(filtered["right_up"], events["right_up"])


def test_gait_segment_endpoint_reuses_cached_model_outputs(monkeypatch):
    class StubAnalyzer:
        @staticmethod
        def analyze(
            phases, strides, poses, fps, return_details=False, spatial_scale=1.0
        ):
            events = {
                "left_down": np.asarray([5.0, 25.0]),
                "left_up": np.asarray([12.0, 32.0]),
                "right_down": np.asarray([15.0, 35.0]),
                "right_up": np.asarray([22.0, 42.0]),
            }
            values = np.asarray([0.5, 0.6])
            samples = {
                "stance_left": values, "stance_right": values,
                "swing_left": values, "swing_right": values,
                "step_time_left": values, "step_time_right": values,
                "double_support": values,
                "step_length_left": values, "step_length_right": values,
                "velocity": np.asarray([1.0]),
                "velocity_weight": np.asarray([len(poses)]),
                "arm_correlation": np.asarray([0.0]),
                "arm_correlation_weight": np.asarray([len(poses)]),
            }
            result = GaitSignalAnalyzer.pool_feature_samples([samples])
            return result, events, samples, {"used_cleaned_events": True}

        pool_feature_samples = staticmethod(GaitSignalAnalyzer.pool_feature_samples)

    monkeypatch.setattr(GaitTask, "get_signal_analyzer", lambda self: StubAnalyzer())

    fps = 30.0
    frame_count = 180
    yaw = np.linspace(0, np.pi, frame_count)
    poses = np.zeros((frame_count, 17, 3), dtype=float)
    axis = np.column_stack([np.cos(yaw), np.zeros(frame_count), np.sin(yaw)])
    for right, left in ((8, 11), (2, 5)):
        poses[:, right] = axis * 500
        poses[:, left] = -axis * 500
    cache = {
        "fps": fps,
        "start_time": 0.0,
        "start_frame_idx": 0,
        "poses3d": poses.tolist(),
        "poses3d_orientation": poses.tolist(),
        "poses3d_mirrored": poses.tolist(),
        "phases": np.zeros((frame_count, 8)).tolist(),
        "strides": np.zeros((frame_count, 9)).tolist(),
        "phases_mirrored": np.zeros((frame_count, 8)).tolist(),
        "strides_mirrored": np.zeros((frame_count, 9)).tolist(),
        "spatial_calibration": {"version": "test", "scale_factor": 0.8},
    }
    payload = {
        "task_data": {"File name": "gait.mp4", "gait_analysis_cache": cache},
        "turning_segment": {
            "is_turning": True,
            "start_time_seconds": 2.0,
            "end_time_seconds": 4.0,
        },
    }
    request = APIRequestFactory().post(
        "/api/update_gait_segments/",
        {"json_data": json.dumps(payload)},
        format="multipart",
    )
    response = update_gait_segments(request)

    assert response.status_code == 200
    assert response.data["gait_analysis_cache"] == cache
    assert response.data["turning_metadata"]["start_frame"] == 60
    assert response.data["turning_metadata"]["end_frame"] == 120
    assert response.data["gait_quality"]["manual_segment_override"] is True
    assert "Steady-step gait time SD (ms)" in response.data
    assert "Steady-step width SD (m; estimated)" not in response.data
    assert "Steady-step width within-segment SD (m; estimated)" in response.data
    assert response.data["gait_quality"]["steady_step_width"]["boundary_exclusion_seconds"] == 2.0
    assert response.data["gait_quality"]["steady_step_gait"]["boundary_exclusion_seconds"] == 2.0
    assert response.data["gait_quality"]["spatial_calibration"] == cache["spatial_calibration"]
    assert len(response.data["segment_metrics"]) == 2


def test_turn_p95_speed_resists_one_frame_orientation_spike():
    task = GaitTask(); task.fps = 30.; task.start_time = 0.; task.start_frame_idx = 0
    yaw = np.linspace(0., 1., 100); yaw[50] += .2
    task._body_yaw = lambda poses: yaw
    result = task.measure_turn_range(np.zeros((100,17,3)),0,99)
    peak = float(np.degrees(np.max(np.abs(np.gradient(yaw,1/30.)))))
    assert result['p95_angular_speed_degrees_per_second'] < peak / 2
    assert 'peak_angular_speed_degrees_per_second' not in result


def test_gait_identity_correction_is_shared_with_display_landmarks():
    task = GaitTask()
    index = {name: i for i, name in enumerate(task._metrabs_joint_order)}
    poses3d = np.zeros((3, 17, 3), dtype=float)
    poses2d = np.zeros((3, 17, 2), dtype=float)
    left, right = index["lwri"], index["rwri"]
    poses3d[:, left, 0] = 500.0
    poses3d[:, right, 0] = -500.0
    poses2d[:, left, 0] = 150.0
    poses2d[:, right, 0] = 50.0
    poses3d[-1, [left, right]] = poses3d[-1, [right, left]]
    poses2d[-1, [left, right]] = poses2d[-1, [right, left]]

    corrected3d, swap_mask = task.correct_left_right_swapping(
        poses3d, window_size=2, margin=100
    )
    corrected2d = task.apply_left_right_swaps(poses2d, swap_mask)

    assert swap_mask[-1, 0]
    assert corrected3d[-1, left, 0] == 500.0
    assert corrected2d[-1, left, 0] == 150.0
