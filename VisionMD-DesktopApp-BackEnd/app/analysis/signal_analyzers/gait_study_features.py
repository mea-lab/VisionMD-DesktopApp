"""Additional study measures, computed independently within each walking segment."""
import numpy as np


def robust(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) >= 4:
        median = np.median(values)
        mad = np.median(np.abs(values - median))
        if mad > 1e-12:
            values = values[np.abs(0.67448975 * (values - median) / mad) <= 4]
    return values


def stride_samples(events, kp, fps):
    # kp is in metres, already ordered as the gait phase skeleton.
    contacts = {side: np.sort(np.asarray(events[side + '_down'], dtype=float)) for side in ('left', 'right')}
    contacts = {s: v[np.isfinite(v) & (v >= 0) & (v < len(kp))] for s, v in contacts.items()}
    all_contacts = np.sort(np.concatenate(list(contacts.values())))
    result = {f'stride_{metric}_{side}': np.array([]) for metric in ('time', 'length') for side in contacts}
    if len(all_contacts) < 3:
        return result
    first, last = np.rint(all_contacts[[0, -1]]).astype(int)
    first, last = np.clip([first, last], 0, len(kp) - 1)
    travel = kp[last, 0, [0, 2]] - kp[first, 0, [0, 2]]
    norm = np.linalg.norm(travel)
    if not np.isfinite(norm) or norm <= 1e-6:
        return result
    for side, joint in (('left', 6), ('right', 3)):
        frames = np.clip(np.rint(contacts[side]).astype(int), 0, len(kp) - 1)
        duration = np.diff(frames) / fps
        displacement = np.abs(np.diff(kp[frames, joint][:, [0, 2]], axis=0) @ (travel / norm))
        valid = (duration > 0) & (duration <= 4) & np.isfinite(displacement)
        # Archived study extension uses reconstructed pose coordinates without
        # the extra height multiplier applied to the routine step length.
        result['stride_time_' + side] = robust(duration[valid])
        result['stride_length_' + side] = robust(displacement[valid])
    return result


def study_segment_summaries(samples):
    left, right = (float(np.asarray(samples.get('arm_swing_' + s, [np.nan]))[0]) for s in ('left', 'right'))
    arm = np.nan
    if np.isfinite(left) and np.isfinite(right) and min(left, right) > 0:
        arm = abs(45 - np.degrees(np.arctan(max(left, right) / min(left, right)))) / 90 * 100
    l, r = (robust(samples.get('step_width_' + s, [])) for s in ('left', 'right'))
    width = np.nan
    if len(l) >= 2 and len(r) >= 2 and l.mean() + r.mean() > 0:
        width = 200 * abs(l.mean() - r.mean()) / (l.mean() + r.mean())
    return {'study_arm_asymmetry': np.array([arm]),
            'study_arm_weight': np.array([len(samples.get('step_time_left', [])) + len(samples.get('step_time_right', []))]),
            'study_width_asymmetry': np.array([width]), 'study_width_weight': np.array([min(len(l), len(r))])}


def pooled_study_features(segments):
    out = {}
    for metric in ('time', 'length'):
        arrays = [robust(s.get(f'stride_{metric}_{side}', [])) for s in segments for side in ('left', 'right')]
        arrays = [x for x in arrays if x.size]
        out['Average stride ' + metric] = float(np.concatenate(arrays).mean()) if arrays else float('nan')
    for label, key in (('Arm-swing amplitude asymmetry (%)', 'arm'), ('Step-width asymmetry (%)', 'width')):
        pairs = [(float(s['study_' + key + '_asymmetry'][0]), float(s['study_' + key + '_weight'][0])) for s in segments if 'study_' + key + '_asymmetry' in s]
        pairs = [(v, w) for v, w in pairs if np.isfinite(v) and w > 0]
        out[label] = float(np.average([v for v, _ in pairs], weights=[w for _, w in pairs])) if pairs else float('nan')
    return out
