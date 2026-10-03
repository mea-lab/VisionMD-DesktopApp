"""Rank tracked people for a reviewable, task-independent suggestion."""
import numpy as np


def rank_subject_candidates(observations, sample_count, frame_area):
    candidates = []
    for person_id, samples in observations.items():
        coverage = len(samples) / max(1, sample_count)
        area = float(np.median([s["area"] for s in samples])) / max(1, frame_area)
        pose_quality = float(np.mean([s["pose_quality"] for s in samples]))
        confidence = float(np.mean([s["confidence"] for s in samples]))
        score = coverage * (.45*pose_quality + .35*np.sqrt(min(1., area)) + .20*confidence)
        candidates.append({"id":person_id,"coverage":coverage,"pose_quality":pose_quality,
                           "mean_confidence":confidence,"score":float(score)})
    return sorted(candidates, key=lambda c: (-c["score"], c["id"]))
