import os
from unittest.mock import patch

from app.analysis import torch_device


def test_auto_prefers_mps_when_cuda_is_unavailable():
    with patch.object(torch_device.torch.cuda, "is_available", return_value=False), \
         patch.object(torch_device, "mps_is_available", return_value=True):
        assert torch_device.preferred_device("auto") == "mps"


def test_unavailable_explicit_mps_falls_back_to_cpu():
    with patch.object(torch_device, "mps_is_available", return_value=False):
        assert torch_device.preferred_device("mps") == "cpu"


def test_recognized_mps_failure_retries_once_on_cpu():
    calls = []
    def operation(device):
        calls.append(device)
        if device == "mps":
            raise NotImplementedError("operator is not implemented for MPS")
        return "ok"
    result, device = torch_device.run_with_device_fallback(operation, "mps")
    assert (result, device) == ("ok", "cpu")
    assert calls == ["mps", "cpu"]


def test_unrelated_error_is_not_retried():
    calls = []
    def operation(device):
        calls.append(device)
        raise RuntimeError("invalid input shape")
    try:
        torch_device.run_with_device_fallback(operation, "mps")
    except RuntimeError as exc:
        assert "invalid input shape" in str(exc)
    else:
        raise AssertionError("unrelated MPS error was incorrectly swallowed")
    assert calls == ["mps"]


def test_environment_override_is_honored():
    with patch.dict(os.environ, {"VISIONMD_TORCH_DEVICE": "cpu"}):
        assert torch_device.preferred_device() == "cpu"

def test_explicitly_mps_marked_value_error_retries_on_cpu():
    calls = []
    def operation(device):
        calls.append(device)
        if device == "mps":
            raise ValueError("operation is not supported on the MPS backend")
        return 42
    result, device = torch_device.run_with_device_fallback(operation, "mps")
    assert (result, device) == (42, "cpu")
    assert calls == ["mps", "cpu"]


def test_mps_failure_disables_future_auto_selection():
    def operation(device):
        if device == "mps":
            raise RuntimeError("MPS operator is not implemented")
        return None
    torch_device.run_with_device_fallback(operation, "mps")
    with patch.object(torch_device.torch.cuda, "is_available", return_value=False), \
         patch.object(torch_device.torch.backends.mps, "is_built", return_value=True), \
         patch.object(torch_device.torch.backends.mps, "is_available", return_value=True):
        assert torch_device.preferred_device("auto") == "cpu"
