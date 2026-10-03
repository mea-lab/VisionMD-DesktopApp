"""Keep the requested physical hand across frame-wise handedness label changes."""
import numpy as np


class HandIdentityTracker:
    """Associate wrist/palm geometry, never individual fingertips, before repair.

    Handedness seeds the track. Once seeded, spatial continuity takes precedence
    over a flickering label. Ambiguous or distant candidates become missing
    observations rather than a skeleton from the other hand.
    """
    PALM = (0, 5, 9, 13, 17)

    def __init__(self, side):
        if side not in ('Left', 'Right'):
            raise ValueError('Hand side must be Left or Right')
        self.side = side
        self.previous = None
        self.scale = None
        self.missed_frames = 0
        self.label_override_count = 0
        self.rejected_frame_count = 0

    def select(self, result, image_width, image_height):
        candidates = []
        for index, landmarks in enumerate(result.hand_landmarks):
            if len(landmarks) != 21 or index >= len(result.handedness):
                continue
            labels = result.handedness[index]
            if not labels:
                continue
            xy = np.asarray([(landmarks[j].x * image_width,
                              landmarks[j].y * image_height) for j in self.PALM])
            scale = float(np.median(np.linalg.norm(xy[1:] - xy[0], axis=1)))
            if not np.isfinite(xy).all() or not np.isfinite(scale) or scale <= 1e-6:
                continue
            candidates.append((index, xy, scale, labels[0].category_name,
                               float(labels[0].score)))
        if self.previous is None:
            eligible = sorted((c for c in candidates if c[3] == self.side),
                              key=lambda c: c[4], reverse=True)
            # Two similarly confident hands with the same label cannot safely
            # establish anatomical identity from this frame alone.
            if not eligible or (len(eligible) > 1 and eligible[0][4] - eligible[1][4] < .1):
                self.rejected_frame_count += 1
                self.missed_frames += 1
                return None
            chosen = eligible[0]
        else:
            ranked = []
            # A detection gap can contain real hand motion. Allow bounded
            # travel since the last observation instead of freezing the gate.
            gap_factor = min(1 + self.missed_frames, 3)
            for candidate in candidates:
                _, xy, scale, label, score = candidate
                if not .5 <= scale / self.scale <= 2:
                    continue
                displacement = float(np.median(np.linalg.norm(xy - self.previous, axis=1))) / self.scale
                if displacement > 1.5 * gap_factor:
                    continue
                # A side-label disagreement is tolerated only very near the
                # established hand. No arbitrary fallback to the other hand.
                if label != self.side and displacement > .75 * gap_factor:
                    continue
                cost = displacement + (.15 if label != self.side else 0)
                ranked.append((cost, candidate))
            ranked.sort(key=lambda entry: entry[0])
            if not ranked or (len(ranked) > 1 and ranked[1][0] - ranked[0][0] < .25):
                self.rejected_frame_count += 1
                self.missed_frames += 1
                return None
            chosen = ranked[0][1]
        self.missed_frames = 0
        index, self.previous, self.scale, label, _ = chosen
        self.label_override_count += int(label != self.side)
        return index
