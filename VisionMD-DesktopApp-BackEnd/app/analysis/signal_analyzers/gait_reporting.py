"""Routine gait outputs versus exploratory estimates and retired aliases."""
DIAGNOSTIC_SD_KEYS = {
    "Step time variability (ms; estimated)", "Step length variability",
    "Step speed variability", "Step width variability",
}
RETIRED_KEYS = {
    "SynthGait step length", "SynthGait step velocity", "L/R mean legacy step length",
    "Legacy step length asymmetry", "Torso medial-lateral displacement",
    "Torso medial-lateral displacement range", "Torso medial-lateral RMS velocity (m/s)",
    "Steady-step width SD (m; estimated)",
    "Turn peak angular speed (deg/s)", "Turn peak speed (deg/s)",
}

def diagnostic_features(data):
    return {key: value for key, value in data.items()
            if key in DIAGNOSTIC_SD_KEYS or "asymmetry" in key.lower()}

STUDY_ASYMMETRY_KEYS = {"Arm-swing amplitude asymmetry (%)", "Step-width asymmetry (%)"}

def public_features(data):
    return {key: value for key, value in data.items()
            if key not in RETIRED_KEYS and key not in DIAGNOSTIC_SD_KEYS
            and ("asymmetry" not in key.lower() or key in STUDY_ASYMMETRY_KEYS)
            and not ("variability" in key.lower() and any(term in key.lower() for term in ("swing time", "stance time", "double support")))}

STUDY_FEATURES = (
    'Average velocity', 'Average cadence', 'Average step length', 'Average stride length',
    'Average step time', 'Average stride time', 'Average stance time', 'Average swing time',
    'Step width', 'Step-width asymmetry (%)', 'Arm swing', 'Arm swing left', 'Arm swing right',
    'Arm-swing amplitude asymmetry (%)', 'Arm swing mean speed (m/s)',
    'Arm swing mean speed left (m/s)', 'Arm swing mean speed right (m/s)',
    'Arm swing P95 speed (m/s)', 'Arm swing P95 speed left (m/s)',
    'Arm swing P95 speed right (m/s)', 'Arm swing correlation',
    'Torso medial-lateral trunk motion ROM', 'Torso medial-lateral mean speed (m/s)',
    'Turn duration (s)', 'Turn mean angular speed (deg/s)',
)

def study_table_features(features, turning):
    """Keep all study rows present; no turn or invalid value is explicitly unavailable."""
    import math
    values = dict(features)
    values['Turn duration (s)'] = turning.get('duration_seconds') if turning.get('is_turning') else None
    values['Turn mean angular speed (deg/s)'] = turning.get('mean_angular_speed_degrees_per_second') if turning.get('is_turning') else None
    for key in STUDY_FEATURES:
        value = values.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            values[key] = None
    return values
