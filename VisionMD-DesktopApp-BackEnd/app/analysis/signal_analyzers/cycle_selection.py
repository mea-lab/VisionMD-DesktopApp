"""Complete-cycle peak selection for periodic motor-task signals.

Candidate generation and filtering remain in ``finder_peaks_signal``. This
module scores complete opening-valley/maximum/closing-valley alternatives,
selects a non-overlapping set globally, and then refines each valley against
local trough depth. The implementation is shared by VisionMD desktop and batch
analysis and mirrored in TestNormalization.
"""

from __future__ import annotations

import bisect
import copy
from dataclasses import dataclass

import numpy as np


_EPS = np.finfo(float).eps

@dataclass(frozen=True)
class CycleOption:
    first_candidate: int
    last_candidate: int
    opening: int
    peak: int
    closing: int
    score: float
    prominence_ratio: float
    height_balance: float
    duration_balance: float
    internal_closure: float

    @property
    def group_size(self):
        return self.last_candidate - self.first_candidate + 1


def _deduplicate_candidates(candidates, distance, velocity):
    """Collapse duplicate peak indices while keeping their outermost valleys."""
    by_peak = {}
    for item in sorted(candidates, key=lambda p: p["peakIndex"]):
        peak = int(item["peakIndex"])
        if peak not in by_peak:
            by_peak[peak] = copy.deepcopy(item)
            continue
        current = by_peak[peak]
        current["openingValleyIndex"] = min(
            current["openingValleyIndex"], item["openingValleyIndex"]
        )
        current["closingValleyIndex"] = max(
            current["closingValleyIndex"], item["closingValleyIndex"]
        )
        current["openingPeakIndex"] = min(
            current.get("openingPeakIndex", peak), item.get("openingPeakIndex", peak)
        )
        current["closingPeakIndex"] = max(
            current.get("closingPeakIndex", peak), item.get("closingPeakIndex", peak)
        )

    result = []
    for peak, item in sorted(by_peak.items()):
        opening = int(item["openingValleyIndex"])
        closing = int(item["closingValleyIndex"])
        if not opening < peak < closing:
            continue
        item.setdefault("openingPeakIndex", peak)
        item.setdefault("closingPeakIndex", peak)
        item["openingMaxSpeedIndex"] = opening + int(
            np.argmax(velocity[opening : peak + 1])
        )
        item["closingMaxSpeedIndex"] = peak + int(
            np.argmin(velocity[peak : closing + 1])
        )
        result.append(item)
    return result


def _deepest_index(distance, start, stop):
    """Index of the deepest sample in inclusive [start, stop]."""
    start = max(0, int(start))
    stop = min(len(distance) - 1, int(stop))
    if stop < start:
        return None
    return start + int(np.argmin(distance[start : stop + 1]))


def _atomic_geometry(candidates, distance):
    peaks = [int(p["peakIndex"]) for p in candidates]
    geometry = []
    for i, peak in enumerate(peaks):
        left_start = peaks[i - 1] + 1 if i else int(candidates[i]["openingValleyIndex"])
        right_stop = peaks[i + 1] - 1 if i + 1 < len(peaks) else int(candidates[i]["closingValleyIndex"])
        opening = _deepest_index(distance, left_start, peak - 1)
        closing = _deepest_index(distance, peak + 1, right_stop)
        if opening is None or closing is None:
            continue
        left_height = float(distance[peak] - distance[opening])
        right_height = float(distance[peak] - distance[closing])
        prominence = max(0.0, min(left_height, right_height))
        geometry.append((opening, peak, closing, prominence))
    return geometry


def _typical_scales(candidates, distance):
    geometry = _atomic_geometry(candidates, distance)
    positive_prominences = np.asarray([g[3] for g in geometry if g[3] > _EPS])
    typical_prominence = (
        float(np.median(positive_prominences))
        if len(positive_prominences)
        else 1.0
    )
    half_spans = []
    for opening, peak, closing, prominence in geometry:
        if prominence > 0.30 * typical_prominence:
            half_spans.extend((peak - opening, closing - peak))
    typical_half_span = float(np.median(half_spans)) if half_spans else 1.0
    return max(typical_prominence, _EPS), max(typical_half_span, 1.0)


def _internal_closure(candidates, first, last, distance, opening, closing):
    if first == last:
        return 1.0
    closures = []
    outer_baseline = min(float(distance[opening]), float(distance[closing]))
    for index in range(first, last):
        left = int(candidates[index]["peakIndex"])
        right = int(candidates[index + 1]["peakIndex"])
        valley = _deepest_index(distance, left, right)
        smaller_peak = min(float(distance[left]), float(distance[right]))
        height = smaller_peak - outer_baseline
        closure = (
            (smaller_peak - float(distance[valley])) / height
            if height > _EPS else 1.0
        )
        closures.append(float(np.clip(closure, 0.0, 1.5)))
    return float(np.mean(closures))


def _build_options(
    candidates,
    distance,
    *,
    max_group_size=4,
    cycle_cost=2.20,
    group_cost=0.12,
):
    typical_prominence, typical_half_span = _typical_scales(candidates, distance)
    candidate_max_excursions = []
    for candidate in candidates:
        candidate_peak = int(candidate["peakIndex"])
        candidate_max_excursions.append(max(
            float(distance[candidate_peak] - distance[int(candidate["openingValleyIndex"])]),
            float(distance[candidate_peak] - distance[int(candidate["closingValleyIndex"])]),
        ))
    typical_max_excursion = max(float(np.median(candidate_max_excursions)), _EPS)
    peaks = [int(p["peakIndex"]) for p in candidates]
    options = []

    for first in range(len(candidates)):
        for last in range(first, min(len(candidates), first + max_group_size)):
            group_peaks = peaks[first : last + 1]
            representative_index = max(
                range(first, last + 1),
                key=lambda index: float(distance[peaks[index]]),
            )
            original = candidates[representative_index]
            peak = int(original["peakIndex"])
            left_start = (
                peaks[first - 1] + 1
                if first
                else int(candidates[first]["openingValleyIndex"])
            )
            right_stop = (
                peaks[last + 1] - 1
                if last + 1 < len(peaks)
                else int(candidates[last]["closingValleyIndex"])
            )
            if last > first:
                left_start = max(
                    left_start, int(candidates[first]["openingValleyIndex"])
                )
                right_stop = min(
                    right_stop, int(candidates[last]["closingValleyIndex"])
                )
            opening = _deepest_index(distance, left_start, group_peaks[0] - 1)
            closing = _deepest_index(distance, group_peaks[-1] + 1, right_stop)
            if opening is None or closing is None or not opening < peak < closing:
                continue
            left_height = float(distance[peak] - distance[opening])
            right_height = float(distance[peak] - distance[closing])
            if left_height <= _EPS or right_height <= _EPS:
                continue
            original_peak = int(original["peakIndex"])
            original_left = float(
                distance[original_peak] - distance[int(original["openingValleyIndex"])]
            )
            original_right = float(
                distance[original_peak] - distance[int(original["closingValleyIndex"])]
            )
            original_balance = (
                min(original_left, original_right) / max(original_left, original_right)
                if max(original_left, original_right) > _EPS else 0.0
            )
            prominence = min(left_height, right_height)
            prominence_ratio = prominence / typical_prominence
            height_balance = min(left_height, right_height) / max(left_height, right_height)
            opening_span = peak - opening
            closing_span = closing - peak
            duration_balance = min(opening_span, closing_span) / max(opening_span, closing_span)
            span_ratio = (opening_span + closing_span) / (2.0 * typical_half_span)
            width_score = float(np.exp(-0.45 * abs(np.log(max(span_ratio, _EPS)))))
            internal_closure = _internal_closure(
                candidates, first, last, distance, opening, closing
            )
            if last > first and internal_closure >= 0.55:
                continue

            # A complete, balanced cycle clears the fixed selection cost. Tiny
            # or one-sided cycles do not. Merged alternatives receive a bonus
            # only when their internal valleys show incomplete closure.
            score = (
                2.20 * min(prominence_ratio, 2.0)
                + 1.10 * height_balance
                + 0.45 * duration_balance
                + 0.35 * width_score
                - cycle_cost
                - group_cost * (last - first)
            )
            if last > first:
                score += 1.35 * max(0.0, 0.60 - internal_closure)
            else:
                score += 0.06
            original_max_ratio = max(original_left, original_right) / typical_max_excursion
            if (
                first == last == len(candidates) - 1
                and original_max_ratio >= 0.30
                and original_balance >= 0.30
            ):
                score += 1.20

            options.append(
                CycleOption(
                    first, last, opening, peak, closing, float(score),
                    float(prominence_ratio), float(height_balance),
                    float(duration_balance), float(internal_closure),
                )
            )
    return options, typical_prominence, typical_half_span


def _weighted_interval_selection(options):
    """Highest-scoring non-overlapping set of complete cycle intervals."""
    ordered = sorted(options, key=lambda o: (o.closing, o.opening, -o.score))
    closings = [option.closing for option in ordered]
    predecessors = [
        bisect.bisect_right(closings, option.opening, hi=index) - 1
        for index, option in enumerate(ordered)
    ]
    best = [0.0] * (len(ordered) + 1)
    take = [False] * len(ordered)
    for index, option in enumerate(ordered, 1):
        include = option.score + best[predecessors[index - 1] + 1]
        exclude = best[index - 1]
        if option.score > 0 and include > exclude + 1e-12:
            best[index] = include
            take[index - 1] = True
        else:
            best[index] = exclude

    selected = []
    index = len(ordered)
    while index:
        option = ordered[index - 1]
        predecessor = predecessors[index - 1]
        include = option.score + best[predecessor + 1]
        if option.score > 0 and include > best[index - 1] + 1e-12:
            selected.append(option)
            index = predecessor + 1
        else:
            index -= 1
    return sorted(selected, key=lambda o: o.peak)


def _is_complete_cycle_rescue(
    option, candidates, distance, typical_half_span
):
    if option.group_size != 1:
        return False
    candidate = candidates[option.first_candidate]
    peak = int(candidate["peakIndex"])
    left = float(distance[peak] - distance[int(candidate["openingValleyIndex"])])
    right = float(distance[peak] - distance[int(candidate["closingValleyIndex"])])
    balance = min(left, right) / max(left, right) if max(left, right) > _EPS else 0.0
    boundary_extension = max(
        int(candidate["openingValleyIndex"]) - option.opening,
        option.closing - int(candidate["closingValleyIndex"]),
    )
    return (
        balance < 0.25
        and option.height_balance >= 0.75
        and option.prominence_ratio >= 1.50
        and option.score >= 2.50
        and boundary_extension >= 2.0 * typical_half_span
    )


def _postselection_confidence(
    options, candidates, distance, typical_half_span
):
    """Remove globally selected cycles with independently weak evidence."""
    kept = []
    rejected = []
    atomic_max_excursions = []
    for candidate in candidates:
        peak = int(candidate["peakIndex"])
        atomic_max_excursions.append(max(
            float(distance[peak] - distance[int(candidate["openingValleyIndex"])]),
            float(distance[peak] - distance[int(candidate["closingValleyIndex"])]),
        ))
    typical_max_excursion = max(float(np.median(atomic_max_excursions)), _EPS)
    for option_index, option in enumerate(options):
        reason = None
        if option.group_size == 1:
            candidate = candidates[option.first_candidate]
            peak = int(candidate["peakIndex"])
            left = float(distance[peak] - distance[int(candidate["openingValleyIndex"])])
            right = float(distance[peak] - distance[int(candidate["closingValleyIndex"])])
            balance = min(left, right) / max(left, right) if max(left, right) > _EPS else 0.0
            max_ratio = max(left, right) / typical_max_excursion
            rhythm_supported = False
            if 0 < option_index < len(options) - 1:
                left_spacing = option.peak - options[option_index - 1].peak
                right_spacing = options[option_index + 1].peak - option.peak
                rhythm_supported = (
                    min(left_spacing, right_spacing)
                    / max(left_spacing, right_spacing) >= 0.75
                    and option.score >= 0.25
                )
            complete_cycle_rescue = _is_complete_cycle_rescue(
                option, candidates, distance, typical_half_span
            )
            if max_ratio < 0.30 and not rhythm_supported:
                reason = "small_amplitude"
            elif balance < 0.25 and not complete_cycle_rescue:
                reason = "weak_original_lobe"
            elif option.score < 0.15 and option.height_balance < 0.50:
                reason = "near_zero_score"
        if (
            reason is None
            and option.first_candidate == 0
            and option.duration_balance < 0.25
        ):
            reason = "leading_temporal_imbalance"
        if (
            reason is None
            and option.last_candidate == len(candidates) - 1
            and option.duration_balance < 0.25
            and option.prominence_ratio < 0.50
        ):
            reason = "weak_trailing_cycle"
        if reason:
            rejected.append({"peak_index": option.peak, "reason": reason, "score": option.score})
        else:
            kept.append(option)

    if len(kept) >= 3:
        peak_indices = np.asarray([option.peak for option in kept])
        spacing_reference = float(np.quantile(np.diff(peak_indices), 0.75))
        compressed = set()
        for index in range(1, len(kept) - 1):
            if (
                kept[index].group_size == 1
                and peak_indices[index] - peak_indices[index - 1] <= 0.35 * spacing_reference
                and peak_indices[index + 1] - peak_indices[index] <= 0.35 * spacing_reference
            ):
                compressed.add(index)
        if compressed:
            filtered = []
            for index, option in enumerate(kept):
                if index in compressed:
                    rejected.append({
                        "peak_index": option.peak,
                        "reason": "compressed_burst_subpeak",
                        "score": option.score,
                    })
                else:
                    filtered.append(option)
            kept = filtered
    return kept, rejected


def _to_peak(option, velocity, candidates, distance):
    opening, peak, closing = option.opening, option.peak, option.closing
    # The option representative is the highest observed maximum in the bout.
    # Production peak-edge intervals can span a shoulder or another maximum,
    # so their geometric midpoint is not guaranteed to be a signal maximum.
    return {
        "openingPeakIndex": peak,
        "closingPeakIndex": peak,
        "openingValleyIndex": opening,
        "openingMaxSpeedIndex": opening + int(np.argmax(velocity[opening : peak + 1])),
        "closingValleyIndex": closing,
        "closingMaxSpeedIndex": peak + int(np.argmin(velocity[peak : closing + 1])),
        "peakIndex": peak,
    }


def refine_independent_valleys(
    peaks,
    distance,
    audit,
    *,
    merged_peak_indices=frozenset(),
    minimum_opposite_side_fraction=0.65,
    minimum_deepest_opening_fraction=0.85,
    minimum_deepest_closing_fraction=0.85,
):
    """Refine opening and closing valleys independently after all production filters.

    The nearest local minimum is used only when it produces a substantial
    excursion and is nearly as deep as the best trough in the local search
    interval. This skips rising and falling shoulders without always forcing
    the absolute deepest point. The first cycle's search is span-limited so a
    distant idle plateau cannot become its opening boundary. Boundaries of
    intentionally merged cycles retain the group's outer valleys.
    """
    refined = copy.deepcopy(peaks)
    if not refined or len(distance) < 3:
        return refined
    minima = np.flatnonzero(
        (distance[1:-1] <= distance[:-2])
        & (distance[1:-1] <= distance[2:])
    ) + 1
    half_spans = [
        span
        for peak in refined
        for span in (
            peak["peakIndex"] - peak["openingValleyIndex"],
            peak["closingValleyIndex"] - peak["peakIndex"],
        )
        if span > 0
    ]
    typical_half_span = float(np.median(half_spans)) if half_spans else 1.0

    for index, peak in enumerate(refined):
        peak_index = peak["peakIndex"]
        if peak_index in merged_peak_indices:
            continue
        center = distance[peak_index]

        left_limit = (
            refined[index - 1]["peakIndex"]
            if index
            else max(0, int(peak_index - 2.5 * typical_half_span))
        )
        opening_candidates = minima[(minima > left_limit) & (minima < peak_index)]
        old_opening = peak["openingValleyIndex"]
        new_opening = old_opening
        if len(opening_candidates):
            closing_excursion = max(
                center - distance[peak["closingValleyIndex"]],
                np.finfo(float).eps,
            )
            deepest_opening_excursion = max(
                center - distance[opening_candidates]
            )
            for candidate in opening_candidates[::-1]:
                opening_excursion = center - distance[candidate]
                if (
                    opening_excursion / closing_excursion >= minimum_opposite_side_fraction
                    and opening_excursion
                    >= minimum_deepest_opening_fraction * deepest_opening_excursion
                ):
                    new_opening = int(candidate)
                    break
        peak["openingValleyIndex"] = new_opening
        if new_opening != old_opening:
            audit.append(
                {
                    "action": "refine_opening_valley",
                    "peak_index": int(peak_index),
                    "old_valley_index": int(old_opening),
                    "new_valley_index": int(new_opening),
                }
            )

        right_limit = (
            refined[index + 1]["peakIndex"]
            if index + 1 < len(refined)
            else max(peak["closingValleyIndex"] + 1, peak_index + 2)
        )
        closing_candidates = minima[(minima > peak_index) & (minima < right_limit)]
        old_closing = peak["closingValleyIndex"]
        new_closing = old_closing
        opening_excursion = max(
            center - distance[peak["openingValleyIndex"]],
            np.finfo(float).eps,
        )
        deepest_closing_excursion = (
            max(center - distance[closing_candidates])
            if len(closing_candidates)
            else 0.0
        )
        for candidate in closing_candidates:
            closing_excursion = center - distance[candidate]
            if (
                closing_excursion / opening_excursion
                >= minimum_opposite_side_fraction
                and closing_excursion
                >= minimum_deepest_closing_fraction * deepest_closing_excursion
            ):
                new_closing = int(candidate)
                break
        peak["closingValleyIndex"] = new_closing
        if new_closing != old_closing:
            audit.append(
                {
                    "action": "refine_closing_valley",
                    "peak_index": int(peak_index),
                    "old_valley_index": int(old_closing),
                    "new_valley_index": int(new_closing),
                }
            )

    return refined

def select_complete_cycles(candidates, distance, velocity):
    """Return the highest-scoring non-overlapping complete movement cycles."""
    atomic = _deduplicate_candidates(candidates, distance, velocity)
    options, _typical_prominence, typical_half_span = _build_options(
        atomic, distance
    )
    selected = _weighted_interval_selection(options)
    selected, _rejections = _postselection_confidence(
        selected, atomic, distance, typical_half_span
    )
    peaks = []
    for option in selected:
        peak = _to_peak(option, velocity, atomic, distance)
        peak["_protectOuterValleys"] = (
            option.group_size > 1
            or _is_complete_cycle_rescue(
                option, atomic, distance, typical_half_span
            )
        )
        peaks.append(peak)
    return peaks


def finalize_cycle_valleys(peaks, distance):
    """Refine valleys, reject exceptional edge cycles, and remove metadata."""
    protected = {
        peak["peakIndex"]
        for peak in peaks
        if peak.get("_protectOuterValleys", False)
    }
    refined = refine_independent_valleys(
        peaks, distance, [], merged_peak_indices=protected
    )
    refined = remove_edge_cycle_outliers(refined, distance)
    for peak in refined:
        peak.pop("_protectOuterValleys", None)
    return refined


def remove_edge_cycle_outliers(peaks, distance, audit=None):
    """Remove an exceptional first or last cycle from an established bout.

    Patients may make a test movement before the instructed bout or one slow
    movement after being asked to stop. Only edge cycles are eligible, and at
    least three interior cycles establish the recording-specific reference.
    A single modest difference is insufficient: amplitude outliers need a
    second geometric abnormality, while duration/gap outliers must be extreme.
    """
    result = copy.deepcopy(peaks)
    if len(result) < 5:
        return result
    audit = audit if audit is not None else []
    interior = result[1:-1]
    epsilon = np.finfo(float).eps

    def features(peak):
        center = int(peak["peakIndex"])
        opening = int(peak["openingValleyIndex"])
        closing = int(peak["closingValleyIndex"])
        left = max(0.0, float(distance[center] - distance[opening]))
        right = max(0.0, float(distance[center] - distance[closing]))
        opening_span = center - opening
        closing_span = closing - center
        return {
            "amplitude": min(left, right),
            "duration": closing - opening,
            "height_balance": min(left, right) / max(left, right, epsilon),
            "duration_balance": min(opening_span, closing_span)
            / max(opening_span, closing_span, 1),
        }

    reference = [features(peak) for peak in interior]
    typical_amplitude = max(
        float(np.median([item["amplitude"] for item in reference])), epsilon
    )
    typical_duration = max(
        float(np.median([item["duration"] for item in reference])), 1.0
    )
    peak_indices = np.asarray([int(peak["peakIndex"]) for peak in result])
    spacings = np.diff(peak_indices)
    interior_spacings = spacings[1:-1] if len(spacings) > 2 else spacings
    typical_spacing = max(float(np.median(interior_spacings)), 1.0)

    rejected = set()
    for index, side in ((0, "leading"), (len(result) - 1, "trailing")):
        item = features(result[index])
        amplitude_ratio = item["amplitude"] / typical_amplitude
        duration_ratio = item["duration"] / typical_duration
        gap = spacings[0] if index == 0 else spacings[-1]
        gap_ratio = float(gap) / typical_spacing

        corroborated_amplitude_outlier = (
            (amplitude_ratio < 0.40 or amplitude_ratio > 2.00)
            and (
                duration_ratio < 0.55
                or duration_ratio > 1.80
                or gap_ratio < 0.65
                or gap_ratio > 1.70
                or item["duration_balance"] < 0.35
            )
        )
        extreme_duration_outlier = duration_ratio > 2.40 and (
            gap_ratio > 1.35
            or item["duration_balance"] < 0.30
            or amplitude_ratio < 0.85
        )
        isolated_edge_cycle = gap_ratio > 2.40 and duration_ratio > 1.60
        # This check intentionally runs after independent valley refinement.
        # A first/last candidate can look acceptable before refinement and then
        # end with one valley sitting on a high shoulder while the opposite
        # valley reaches the bout baseline. Such a one-sided edge cycle is an
        # incomplete test/stop movement, even when its timing and smaller
        # excursion otherwise resemble the established bout.
        vertically_asymmetric_edge = item["height_balance"] < 0.70
        if not (
            corroborated_amplitude_outlier
            or extreme_duration_outlier
            or isolated_edge_cycle
            or vertically_asymmetric_edge
        ):
            continue
        rejected.add(index)
        audit.append({
            "action": "remove_edge_cycle_outlier",
            "side": side,
            "peak_index": int(result[index]["peakIndex"]),
            "amplitude_ratio": float(amplitude_ratio),
            "duration_ratio": float(duration_ratio),
            "spacing_ratio": float(gap_ratio),
            "height_balance": float(item["height_balance"]),
            "duration_balance": float(item["duration_balance"]),
        })
    return [peak for index, peak in enumerate(result) if index not in rejected]
