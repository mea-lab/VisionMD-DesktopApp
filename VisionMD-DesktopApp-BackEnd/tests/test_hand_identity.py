from types import SimpleNamespace as S

from app.analysis.detectors.hand_identity import HandIdentityTracker


def result(*hands):
    return S(hand_landmarks=[h[0] for h in hands], handedness=[[h[1]] for h in hands])


def hand(x, y, label='Right', score=.95):
    pts = [S(x=x, y=y)] + [S(x=x + .02 * ((i % 4) - 1), y=y - .05) for i in range(1, 21)]
    return pts, S(category_name=label, score=score)


def test_duplicate_right_labels_keep_physical_hand_when_order_changes():
    tracker = HandIdentityTracker('Right')
    assert tracker.select(result(hand(.3, .4), hand(.7, .6, 'Left')), 1000, 1000) == 0
    assert tracker.select(result(hand(.7, .6, score=.99), hand(.301, .4)), 1000, 1000) == 1


def test_side_label_flip_does_not_switch_to_other_hand():
    tracker = HandIdentityTracker('Right')
    tracker.select(result(hand(.3, .4)), 1000, 1000)
    assert tracker.select(result(hand(.7, .6), hand(.301, .4, 'Left')), 1000, 1000) == 1
    assert tracker.label_override_count == 1


def test_other_hand_only_is_missing_not_a_fallback():
    tracker = HandIdentityTracker('Right')
    tracker.select(result(hand(.3, .4)), 1000, 1000)
    assert tracker.select(result(hand(.7, .6)), 1000, 1000) is None
    assert tracker.select(result(hand(.302, .4)), 1000, 1000) == 0


def test_ambiguous_initial_or_tracked_candidates_are_missing():
    tracker = HandIdentityTracker('Right')
    assert tracker.select(result(hand(.3, .4), hand(.7, .6)), 1000, 1000) is None
    tracker.select(result(hand(.3, .4)), 1000, 1000)
    assert tracker.select(result(hand(.301, .4), hand(.302, .4)), 1000, 1000) is None


def test_left_hand_uses_same_association_and_missing_frames_preserve_anchor():
    tracker = HandIdentityTracker('Left')
    assert tracker.select(result(hand(.3, .4, 'Left')), 1000, 1000) == 0
    assert tracker.select(result(), 1000, 1000) is None
    assert tracker.select(result(hand(.301, .4, 'Right')), 1000, 1000) == 0
