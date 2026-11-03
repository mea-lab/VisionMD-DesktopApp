"""Height-calibrated 3D sit-to-stand distances over the selected feature window."""
import numpy as np
from scipy.signal import find_peaks
from ._sit_to_stand import smooth, clean

METRIC_LABELS = {
    'pelvis_excursion_cm': 'Pelvis excursion (cm)',
    'lateral_shift_cm': 'Lateral pelvis range (cm)',
    'mean_ascent_speed_cm_s': 'Mean ascent speed (cm/s)',
    'p95_ascent_speed_cm_s': 'P95 ascent speed (cm/s)',
    'arm_cross_distance_mean_cm': 'Mean crossed-arm distance (cm)',
    'arm_cross_distance_range_cm': 'Crossed-arm distance range (cm)',
}
RELATIVE_KEYS = ('pelvis_excursion_relative', 'lateral_shift_relative',
                 'arm_cross_distance_mean', 'arm_cross_distance_change')
RELATIVE_LABELS = ('Pelvis excursion (relative)', 'Lateral pelvis range (relative)',
                   'Mean crossed-arm distance (relative)', 'Crossed-arm distance range (relative)')


def apply_metric_measurements(result, poses_mm, height_cm):
    """Use entered stature / terminal 3D stature; never use the gait-fitted coefficient.

    Vertical is estimated from the final head-top/ankle axis, not calibrated gravity.
    Pelvis coordinates are relative to the ankle midpoint to reduce camera translation.
    Event boundaries and the 2D normalized research outputs are retained.
    """
    p = np.asarray(poses_mm, dtype=float)
    height_cm = float(height_cm)
    cache = result['sit_to_stand_analysis_cache']
    fps, start = float(cache['fps']), float(cache['start_time'])
    if p.shape != (len(cache['poses2d']), 17, 3) or not np.isfinite(p).all():
        raise ValueError('Metric sit-to-stand measurements require finite, frame-aligned 3D poses.')
    if not np.isfinite(height_cm) or height_cm <= 0:
        raise ValueError('Metric sit-to-stand measurements require positive participant height.')
    sts = result['sit_to_stand']
    a, b = (int(round((sts['feature_window'][k] - start) * fps)) for k in ('start', 'end'))
    stop = min(len(p), b + max(3, round(.3 * fps)))
    ankle = p[:, [10, 13]].mean(axis=1)
    reference = p[b:stop, 0] - ankle[b:stop]
    stature = np.median(np.linalg.norm(p[b:stop, 0, None] - p[b:stop][:, [10, 13]], axis=2).mean(axis=1))
    up = np.median(reference, axis=0)
    if not np.isfinite(stature) or stature <= 1 or np.linalg.norm(up) <= 1:
        raise ValueError('Unable to establish the 3D standing body reference for metric measurements.')
    up /= np.linalg.norm(up)
    lateral = np.median(p[b:stop, 5] - p[b:stop, 2], axis=0)
    lateral -= (lateral @ up) * up
    if np.linalg.norm(lateral) <= 1:
        raise ValueError('Unable to establish the lateral body axis for metric measurements.')
    lateral /= np.linalg.norm(lateral)
    cm_per_model_mm = height_cm / float(stature)
    relative_pelvis = smooth(p[:, 14] - ankle, fps) * cm_per_model_mm
    H = smooth(relative_pelvis @ up, fps)
    velocity = np.gradient(H, 1 / fps, edge_order=2)
    sideways = relative_pelvis @ lateral
    cross = (np.linalg.norm(p[:, 4] - p[:, 5], axis=1) + np.linalg.norm(p[:, 7] - p[:, 2], axis=1)) / 2 * cm_per_model_mm
    cross = smooth(cross, fps)
    segment = slice(a, b + 1)
    v = velocity[segment]
    metrics = {
        'pelvis_excursion_cm': float(H[b] - H[a]),
        'lateral_shift_cm': float(np.ptp(sideways[segment])),
        'mean_ascent_speed_cm_s': float(np.mean(v)),
        'p95_ascent_speed_cm_s': float(np.percentile(v, 95)),
        'arm_cross_distance_mean_cm': float(np.mean(cross[segment])),
        'arm_cross_distance_range_cm': float(np.ptp(cross[segment])),
    }
    sts['relative_features'] = dict(sts['features'])
    sts['relative_signals'] = dict(sts['signals'])
    for key in RELATIVE_KEYS:
        sts['features'].pop(key, None)
    for label in RELATIVE_LABELS:
        result.pop(label, None)
    sts['features'].update(metrics)
    result.update({label: metrics[key] for key, label in METRIC_LABELS.items()})
    # Variability remains dimensionless, now derived from the displayed 3D velocity.
    cv = float(np.std(v) / np.mean(v)) if np.mean(v) > 1e-6 else None
    sts['features']['ascent_speed_cv'] = cv
    result['Ascent velocity coefficient of variation'] = cv
    peaks, _ = find_peaks(np.abs(v), prominence=.1 * np.max(np.abs(v)), distance=max(1, round(.12 * fps)))
    result['Extra pelvis speed peaks'] = sts['features']['extra_speed_peaks'] = max(0, len(peaks) - 1)
    time = sts['signals']['time']
    sts['signals'].update(pelvis_height=H.tolist(), pelvis_velocity=velocity.tolist())
    sts['speed_peaks'] = {'time': [time[a + i] for i in peaks], 'data': velocity[a + peaks].tolist()}
    result['linePlot'] = {'time': time, 'data': H.tolist()}
    result['velocityPlot'] = {'time': time, 'data': velocity.tolist()}
    result['landMarks_3D'] = p.tolist()
    sts['subject_height_cm'] = height_cm
    sts['metric_calibration'] = {
        'version': 'sts-height-reference-v1', 'participant_height_cm': height_cm,
        'model_reference_stature_mm': float(stature), 'cm_per_model_mm': cm_per_model_mm,
        'reference_start_time': time[b], 'reference_end_time': time[stop - 1],
        'vertical_axis': up.tolist(), 'lateral_axis': lateral.tolist(),
        'method': 'entered height / terminal median 3D head-top-to-ankles stature; no gait-fitted coefficient',
        'axis_definition': 'terminal head-top-to-ankle midpoint axis; assumes an upright final reference',
        'measurement_frame': 'ankle-relative 3D body reference',
    }
    sts['quality'].update(metric_scaling='height_calibrated_3d', height_scaling='Applied using entered height and terminal 3D stature.')
    cache['subject_height_cm'] = height_cm
    result['radarTable'] = {k: v for k, v in result['radarTable'].items() if k not in RELATIVE_LABELS}
    result['radarTable'].update({label: metrics[key] for key, label in METRIC_LABELS.items()})
    result['radarTable']['Ascent velocity coefficient of variation'] = cv
    result['radarTable']['Extra pelvis speed peaks'] = result['Extra pelvis speed peaks']
    return clean(result)
