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

def public_features(data):
    return {key: value for key, value in data.items()
            if key not in RETIRED_KEYS and key not in DIAGNOSTIC_SD_KEYS
            and "asymmetry" not in key.lower()
            and not ("variability" in key.lower() and any(term in key.lower() for term in ("swing time", "stance time", "double support")))}
