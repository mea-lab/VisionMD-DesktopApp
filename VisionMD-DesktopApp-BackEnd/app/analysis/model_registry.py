"""Thread-safe process-local registry for expensive immutable model objects."""
from __future__ import annotations

from threading import RLock

_MODELS = {}
_LOCK = RLock()


def get_model(key, factory):
    """Return one initialized model per backend worker and registry key."""
    with _LOCK:
        model = _MODELS.get(key)
        if model is None:
            model = factory()
            _MODELS[key] = model
        return model


def loaded_model_keys():
    with _LOCK:
        return tuple(sorted(_MODELS))


def reset_yolo_runtime(model):
    """Drop per-video predictor/tracker state while retaining loaded weights.

    Ultralytics stores tracking state on the predictor. Reusing that state across
    unrelated videos can transfer track IDs and stale frame geometry. Rebuilding
    the lightweight predictor avoids that leak without paying the cost of loading
    the network weights again.
    """
    model.predictor = None
    return model
