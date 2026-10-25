import numpy as np


def _cycle(opening, peak, closing):
    return {
        "openingPeakIndex": peak,
        "closingPeakIndex": peak,
        "openingValleyIndex": opening,
        "openingMaxSpeedIndex": opening,
        "closingValleyIndex": closing,
        "closingMaxSpeedIndex": closing,
        "peakIndex": peak,
    }


def test_complete_cycle_selection_keeps_periodic_cycles():
    from app.analysis.signal_analyzers.cycle_selection import (
        finalize_cycle_valleys,
        select_complete_cycles,
    )

    distance = np.asarray([0.0, 5.0, 10.0, 5.0, 0.0, 4.0, 9.0, 4.0, 0.0])
    velocity = np.gradient(distance)
    peaks = select_complete_cycles(
        [_cycle(0, 2, 4), _cycle(4, 6, 8)], distance, velocity
    )
    peaks = finalize_cycle_valleys(peaks, distance)

    assert [peak["peakIndex"] for peak in peaks] == [2, 6]
    assert all(
        peak["openingValleyIndex"] < peak["peakIndex"] < peak["closingValleyIndex"]
        for peak in peaks
    )
    assert all("_protectOuterValleys" not in peak for peak in peaks)


def test_closing_refinement_skips_a_shallow_shoulder():
    from app.analysis.signal_analyzers.cycle_selection import finalize_cycle_valleys

    distance = np.asarray([0.0, 5.0, 10.0, 5.0, 3.0, 4.0, 1.0, 4.0, 9.0, 4.0, 0.0])
    peaks = finalize_cycle_valleys(
        [_cycle(0, 2, 4), _cycle(6, 8, 10)], distance
    )

    assert peaks[0]["closingValleyIndex"] == 6

def test_stable_edge_cycles_are_preserved():
    from app.analysis.signal_analyzers.cycle_selection import remove_edge_cycle_outliers

    distance = np.asarray([0.0, 10.0, 0.0, 10.0, 0.0, 10.0,
                           0.0, 10.0, 0.0, 10.0, 0.0])
    peaks = [_cycle(i - 1, i, i + 1) for i in (1, 3, 5, 7, 9)]

    assert [p["peakIndex"] for p in remove_edge_cycle_outliers(peaks, distance)] == [1, 3, 5, 7, 9]


def test_slow_isolated_trailing_test_movement_is_removed():
    from app.analysis.signal_analyzers.cycle_selection import remove_edge_cycle_outliers

    distance = np.zeros(15)
    distance[[1, 3, 5, 7, 11]] = 10.0
    peaks = [_cycle(i - 1, i, i + 1) for i in (1, 3, 5, 7)]
    peaks.append(_cycle(8, 11, 14))
    audit = []

    result = remove_edge_cycle_outliers(peaks, distance, audit)

    assert [p["peakIndex"] for p in result] == [1, 3, 5, 7]
    assert audit[0]["action"] == "remove_edge_cycle_outlier"
    assert audit[0]["side"] == "trailing"


def test_edge_filter_does_not_remove_an_interior_outlier():
    from app.analysis.signal_analyzers.cycle_selection import remove_edge_cycle_outliers

    distance = np.asarray([0.0, 10.0, 0.0, 10.0, 0.0, 30.0,
                           0.0, 10.0, 0.0, 10.0, 0.0])
    peaks = [_cycle(i - 1, i, i + 1) for i in (1, 3, 5, 7, 9)]

    assert [p["peakIndex"] for p in remove_edge_cycle_outliers(peaks, distance)] == [1, 3, 5, 7, 9]


def test_vertically_asymmetric_trailing_edge_is_removed_after_refinement():
    from app.analysis.signal_analyzers.cycle_selection import remove_edge_cycle_outliers

    distance = np.asarray([
        0.0, 10.0, 0.0, 10.0, 0.0, 10.0,
        0.0, 10.0, 0.0, 10.0, 4.0,
    ])
    peaks = [_cycle(i - 1, i, i + 1) for i in (1, 3, 5, 7)]
    peaks.append(_cycle(8, 9, 10))

    result = remove_edge_cycle_outliers(peaks, distance)

    assert [p["peakIndex"] for p in result] == [1, 3, 5, 7]


def test_vertically_asymmetric_leading_edge_is_removed_after_refinement():
    from app.analysis.signal_analyzers.cycle_selection import remove_edge_cycle_outliers

    distance = np.asarray([
        4.0, 10.0, 0.0, 10.0, 0.0, 10.0,
        0.0, 10.0, 0.0, 10.0, 0.0,
    ])
    peaks = [_cycle(i - 1, i, i + 1) for i in (1, 3, 5, 7, 9)]

    result = remove_edge_cycle_outliers(peaks, distance)

    assert [p["peakIndex"] for p in result] == [3, 5, 7, 9]
