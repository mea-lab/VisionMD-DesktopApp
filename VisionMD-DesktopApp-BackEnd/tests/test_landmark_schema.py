from app.analysis.landmark_schema import attach_landmark_schema


def test_gait_schema_separates_display_analysis_and_orientation_landmarks():
    payload = {
        "landMarks": [[[1.0, 2.0]]],
        "landMarks_3D": [[[1.0, 2.0, 3.0]]],
        "gait_analysis_cache": {"poses3d_orientation": [[[1.0, 2.0, 3.0]]]},
    }

    attach_landmark_schema(payload, "gait")

    schema = payload["landmarkSchema"]
    assert schema["display"]["key"] == "landMarks"
    assert schema["analysis"]["key"] == "landMarks_3D"
    assert schema["orientation"]["key"] == "gait_analysis_cache.poses3d_orientation"
    assert schema["manualEditing"]["supported"] is False


def test_classic_2d_task_declares_shared_editable_analysis_landmarks():
    payload = {"landMarks": [[[1.0, 2.0]]], "allLandMarks": [[[1.0, 2.0, 0.0]]]}

    attach_landmark_schema(payload, "finger_tap_left")

    schema = payload["landmarkSchema"]
    assert schema["display"]["key"] == schema["analysis"]["key"] == "landMarks"
    assert schema["normalization"]["key"] == "allLandMarks"
    assert schema["manualEditing"]["supported"] is True


def test_pronation_schema_prevents_2d_edits_from_corrupting_cached_angles():
    payload = {"landMarks": [[[1.0, 2.0, 0.0, 0.0, 0.0, 45.0]]]}

    attach_landmark_schema(payload, "hand_pronation_right")

    schema = payload["landmarkSchema"]
    assert schema["analysis"]["signalComponent"] == "angle"
    assert schema["manualEditing"]["supported"] is False
