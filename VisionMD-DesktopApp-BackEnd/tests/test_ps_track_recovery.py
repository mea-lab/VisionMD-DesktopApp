import numpy as np
import pytest
from app.analysis.tasks._ps_track_recovery import select_recovery_track
from app.analysis.tasks._ps_hand_search import track_search_quality


def fixture_tracks():
    moving = {i: np.array([100+i,100,150+i,150.]) for i in range(60)}
    samples = {i: [np.array([500,500,550,550.]), box, box+[1,1,-1,-1]]
               for i, box in moving.items()}
    return moving, samples


def test_reference_identity_beats_high_confidence_other_hand_and_duplicates():
    moving, samples = fixture_tracks()
    reference = [(i,b) for i,b in moving.items() if i % 3 != 0]
    confidence = {i: [.99,.8,.1] for i in samples}
    track = select_recovery_track(samples, fps=30, reference_track=reference,
                                  confidences=confidence)
    assert len(track) == 60
    assert all(np.array_equal(box, moving[i]) for i,box in track)


def test_recovery_does_not_invent_detections_across_long_gap():
    moving, samples = fixture_tracks()
    samples = {i:b for i,b in samples.items() if i < 20 or i > 42}
    reference = [(i,moving[i]) for i in samples]
    track = select_recovery_track(samples, fps=30, reference_track=reference)
    assert all(i in samples for i,_ in track)
    quality = track_search_quality(track,60,1,30,[0,0,1000,1000],1000,1000)
    assert not quality['pass']


def test_recovery_requires_participant_reference():
    _, samples = fixture_tracks()
    with pytest.raises(RuntimeError, match='reference'):
        select_recovery_track(samples, fps=30, reference_track=[])
