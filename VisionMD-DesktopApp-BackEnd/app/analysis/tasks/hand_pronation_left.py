"""Left hand pronation/supination task."""

from ._pronation_supination import HandPronationSupinationTask


class HandPronationLeftTask(HandPronationSupinationTask):
    HAND_LABEL = "Left"
