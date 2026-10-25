"""Shared PyTorch accelerator selection with safe Apple MPS fallback."""
from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import TypeVar

# Let PyTorch itself execute unsupported MPS operators on CPU when it can. This
# must be set before importing torch to affect backend initialization.
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import torch

LOGGER = logging.getLogger(__name__)
T = TypeVar("T")
_MPS_DISABLED_REASON = None
_MPS_ERROR_MARKERS = (
    "mps",
    "metal",
    "placeholder storage",
    "not implemented",
    "not supported",
    "unsupported",
)


def mps_is_available(*, probe: bool = True) -> bool:
    """Return whether MPS is built, available, and can execute a basic op."""
    global _MPS_DISABLED_REASON
    if _MPS_DISABLED_REASON is not None:
        return False
    backend = getattr(getattr(torch, "backends", None), "mps", None)
    if backend is None:
        return False
    try:
        if not backend.is_built() or not backend.is_available():
            return False
        if probe:
            value = (torch.ones(1, device="mps") + 1).cpu()
            if float(value[0]) != 2.0:
                return False
            synchronize = getattr(getattr(torch, "mps", None), "synchronize", None)
            if synchronize is not None:
                synchronize()
        return True
    except Exception as exc:
        _MPS_DISABLED_REASON = f"MPS availability probe: {exc}"
        LOGGER.warning("Apple MPS probe failed; using CPU instead: %s", exc)
        return False


def preferred_device(requested: str | torch.device | None = None) -> str:
    """Resolve ``auto`` to CUDA, Apple MPS, then CPU, with availability checks."""
    configured = requested if requested is not None else os.environ.get(
        "VISIONMD_TORCH_DEVICE", "auto"
    )
    value = str(configured).strip().lower()
    if not value:
        value = "auto"
    if value.isdigit():
        value = f"cuda:{value}"
    if value == "auto":
        if torch.cuda.is_available():
            return "cuda"
        if mps_is_available():
            return "mps"
        return "cpu"
    if value.startswith("cuda"):
        if torch.cuda.is_available():
            return value
        LOGGER.warning("CUDA was requested but is unavailable; selecting another backend")
        return "mps" if mps_is_available() else "cpu"
    if value.startswith("mps"):
        if mps_is_available():
            return value
        LOGGER.warning("Apple MPS was requested but is unavailable; using CPU")
        return "cpu"
    if value == "cpu":
        return "cpu"
    raise ValueError(f"Unsupported Torch device {configured!r}; use auto, cpu, cuda, cuda:N, or mps")


def is_mps_failure(exc: BaseException) -> bool:
    """Identify backend/operation failures that are safe to retry on CPU."""
    if isinstance(exc, NotImplementedError):
        return True
    if not isinstance(exc, (RuntimeError, TypeError, ValueError, AssertionError)):
        return False
    message = str(exc).lower()
    return any(marker in message for marker in _MPS_ERROR_MARKERS)


def clear_mps_cache() -> None:
    empty_cache = getattr(getattr(torch, "mps", None), "empty_cache", None)
    if empty_cache is not None:
        try:
            empty_cache()
        except Exception:
            LOGGER.debug("Unable to clear the MPS cache", exc_info=True)


def run_with_device_fallback(
    operation: Callable[[str], T],
    device: str | torch.device,
    *,
    label: str = "inference",
    on_cpu_fallback: Callable[[], None] | None = None,
) -> tuple[T, str]:
    """Run on ``device`` and retry once on CPU for recognized MPS failures.

    Non-MPS failures and unrelated application errors are never swallowed.
    The returned device should be retained by callers so subsequent batches do
    not repeatedly attempt a backend that already failed.
    """
    selected = str(device)
    try:
        return operation(selected), selected
    except Exception as exc:
        if not selected.startswith("mps") or not is_mps_failure(exc):
            raise
        global _MPS_DISABLED_REASON
        _MPS_DISABLED_REASON = f"{label}: {exc}"
        LOGGER.warning(
            "%s failed on Apple MPS (%s); retrying on CPU and disabling MPS "
            "for subsequent model loads in this process", label, exc
        )
        clear_mps_cache()
        if on_cpu_fallback is not None:
            on_cpu_fallback()
        return operation("cpu"), "cpu"
