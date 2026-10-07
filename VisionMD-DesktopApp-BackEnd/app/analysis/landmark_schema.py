"""Describe which persisted landmarks are displayed, analyzed, and editable."""


EDITABLE_2D_TASKS = {
    "finger_tap_left",
    "finger_tap_right",
    "hand_movement_left",
    "hand_movement_right",
    "leg_agility_left",
    "leg_agility_right",
    "toe_tapping_left",
    "toe_tapping_right",
}


def attach_landmark_schema(payload, task_key):
    """Add non-duplicating landmark role metadata to an analysis response."""
    if not isinstance(payload, dict) or "landMarks" not in payload:
        return payload

    task_key = str(task_key).lower()
    schema = {
        "version": "visionmd-landmark-roles-v1",
        "display": {
            "key": "landMarks",
            "coordinateSpace": "video_pixels",
            "components": ["x", "y"],
        },
        "analysis": {"key": "landMarks", "components": "task-specific"},
        "normalization": {
            "key": "allLandMarks" if "allLandMarks" in payload else None,
        },
        "manualEditing": {
            "supported": task_key in EDITABLE_2D_TASKS,
            "endpoint": "update_landmarks" if task_key in EDITABLE_2D_TASKS else None,
        },
    }

    if task_key == "gait":
        schema.update({
            "display": {
                **schema["display"],
                "identity": "left/right corrected to match analysis landmarks",
            },
            "analysis": {
                "key": "landMarks_3D",
                "coordinateSpace": "camera_3d_millimetres",
                "components": ["x", "y", "z"],
            },
            "orientation": {
                "key": "gait_analysis_cache.poses3d_orientation",
                "purpose": "turn detection before continuity-based left/right correction",
            },
            "normalization": {"key": "gait_analysis_cache.spatial_calibration"},
            "manualEditing": {
                "supported": False,
                "endpoint": None,
                "reason": "2D display edits cannot be propagated safely to 3D gait analysis",
            },
        })
    elif task_key.startswith("hand_tremor_"):
        schema.update({
            "analysis": {
                "key": None,
                "persisted": False,
                "purpose": "tremor analysis uses the full repaired detector track",
            },
            "manualEditing": {
                "supported": False,
                "endpoint": None,
                "reason": "the displayed joint subset is not the complete analysis track",
            },
        })
    elif task_key.startswith("hand_pronation_"):
        schema.update({
            "analysis": {
                "key": "landMarks",
                "components": ["x", "y", "world_x", "world_y", "world_z", "angle"],
                "signalComponent": "angle",
            },
            "manualEditing": {
                "supported": False,
                "endpoint": None,
                "reason": "moving display coordinates cannot update the cached 3D orientation angle",
            },
        })

    payload["landmarkSchema"] = schema
    return payload
