"""Right hand pronation/supination task."""

from ._pronation_supination import HandPronationSupinationTask


class HandPronationRightTask(HandPronationSupinationTask):
    HAND_LABEL = "Right"
