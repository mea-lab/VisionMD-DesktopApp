"""Optional bidirectional temporal refiner for failed WiLoR P/S trajectories.

The model is intentionally a second-stage safety net. The deterministic
YOLO/WiLoR pipeline remains authoritative for trajectories that pass quality
checks. Only failed trajectories are offered to this model, and conservative
post-inference checks can still reject its correction.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import torch
from django.conf import settings
from torch import nn

from app.analysis.torch_device import preferred_device, run_with_device_fallback
from ._wilor_ps_pipeline import (choose_angle_estimator, geometry_angle,
                                 landmark_temporal_decode, palm_normal_angle,
                                 zero_phase_lowpass)


class BiGRURefiner(nn.Module):
    """Architecture matching the validated standalone V3 checkpoint."""

    def __init__(self, input_size: int, hidden_size: int, layers: int, dropout: float):
        super().__init__()
        self.input_norm = nn.LayerNorm(input_size)
        self.gru = nn.GRU(
            input_size, hidden_size, layers, batch_first=True,
            bidirectional=True, dropout=dropout if layers > 1 else 0.0)
        self.head = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size), nn.GELU(),
            nn.Dropout(dropout), nn.Linear(hidden_size, 1))

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        encoded, _ = self.gru(self.input_norm(features))
        return self.head(encoded).squeeze(-1)


_MODEL = None
_MEAN = None
_STD = None
_CHECKPOINT_PATH = None


def _checkpoint_path() -> Path:
    configured = os.environ.get("VISIONMD_PS_TEMPORAL_MODEL")
    if configured:
        return Path(configured)
    return (Path(settings.BASE_DIR) / "app/analysis/models/wilor_temporal/"
            "wilor_bigru_refiner_final.pt")


def _load(device: torch.device):
    global _MODEL, _MEAN, _STD, _CHECKPOINT_PATH
    path = _checkpoint_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"P/S temporal checkpoint not found: {path}. Set VISIONMD_PS_TEMPORAL_MODEL.")
    if _MODEL is None:
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        config = checkpoint["config"]
        _MODEL = BiGRURefiner(
            checkpoint["input_size"], config["hidden_size"],
            config["layers"], config["dropout"])
        _MODEL.load_state_dict(checkpoint["model"])
        _MEAN = torch.as_tensor(checkpoint["mean"])
        _STD = torch.as_tensor(checkpoint["std"])
        _CHECKPOINT_PATH = str(path)
    # Moving an already cached model is important when an MPS operation fails:
    # the retry must migrate parameters and normalization tensors to CPU.
    _MODEL.to(device).eval()
    _MEAN = _MEAN.to(device)
    _STD = _STD.to(device)
    return _MODEL, _MEAN, _STD


def _center_initial(values: np.ndarray, fps: float) -> np.ndarray:
    count = max(1, min(len(values), round(0.5 * fps)))
    return values - np.median(values[:count])


def _features(raw: np.ndarray, rois: np.ndarray, baseline: np.ndarray,
              right: bool, fps: float) -> np.ndarray:
    corrected, diagnostics = landmark_temporal_decode(raw)
    geometry = np.degrees(np.unwrap(np.radians(geometry_angle(corrected, False))))
    raw_geometry = np.degrees(np.unwrap(np.radians(geometry_angle(raw, False))))
    palm = np.degrees(np.unwrap(np.radians(palm_normal_angle(raw, right))))
    observation, _, _, _ = choose_angle_estimator(geometry, palm, raw_geometry)
    wrist = raw[:, :1]
    scale = np.linalg.norm(raw[:, 9] - raw[:, 0], axis=1).clip(1e-6)
    normalized = (raw - wrist) / scale[:, None, None]
    velocity = np.diff(normalized, axis=0, prepend=normalized[:1])
    radians = np.radians(np.column_stack((geometry, palm, observation)))
    angle_features = np.column_stack((np.sin(radians), np.cos(radians)))
    centers = (rois[:, :2] + rois[:, 2:]) / 2
    sides = np.max(rois[:, 2:] - rois[:, :2], axis=1).clip(1)
    roi_features = np.column_stack((
        (centers - np.median(centers, axis=0)) / np.median(sides),
        np.log(sides / np.median(sides))))
    diagnostic_features = np.column_stack((
        diagnostics["landmark_quality_score"], diagnostics["landmark_step_raw"],
        diagnostics["bone_length_relative_error"],
        diagnostics["branch_flipped"].astype(float)))
    return np.column_stack((
        normalized.reshape(len(raw), -1), velocity.reshape(len(raw), -1),
        angle_features, diagnostic_features, roi_features,
        _center_initial(observation, fps) / 180.0,
        np.full(len(raw), 1.0 if right else -1.0))).astype(np.float32)


def refine_failed_trajectory(raw: np.ndarray, rois: np.ndarray,
                             baseline: np.ndarray, right: bool,
                             fps: float) -> tuple[np.ndarray, dict]:
    """Return a refined relative angle and explicit acceptance diagnostics."""
    feature_values = _features(raw, rois, baseline, right, fps)
    baseline_relative = _center_initial(np.asarray(baseline, float), fps)

    def infer(active_device: str) -> np.ndarray:
        device = torch.device(active_device)
        model, mean, std = _load(device)
        features = torch.as_tensor(feature_values, device=device)
        inputs = (features - mean) / std
        base = torch.as_tensor(
            baseline_relative / 180.0, device=device, dtype=torch.float32)
        with torch.no_grad(), torch.autocast(
                device_type=device.type, dtype=torch.bfloat16,
                enabled=device.type == "cuda"):
            return (base + model(inputs[None])[0]).float().cpu().numpy() * 180.0

    refined, actual_device = run_with_device_fallback(
        infer, preferred_device(), label="P/S temporal refiner inference")
    refined, cutoff = zero_phase_lowpass(refined, fps, 10.0)
    base_steps = np.abs(np.diff(baseline_relative))
    refined_steps = np.abs(np.diff(refined))
    base_range = float(np.percentile(baseline_relative, 95)-np.percentile(baseline_relative, 5))
    refined_range = float(np.percentile(refined, 95)-np.percentile(refined, 5))
    correlation = float(np.corrcoef(baseline_relative, refined)[0, 1])
    reasons = []
    if not np.all(np.isfinite(refined)):
        reasons.append("nonfinite_output")
    if refined_range > max(360.0, 1.10 * base_range):
        reasons.append("range_expanded")
    base_max = float(base_steps.max()) if len(base_steps) else 0.0
    refined_max = float(refined_steps.max()) if len(refined_steps) else 0.0
    if refined_max > max(90.0, 1.25 * base_max):
        reasons.append("step_worsened")
    if correlation < 0.75:
        reasons.append("trajectory_replaced")
    accepted = not reasons
    diagnostics = {
        "attempted": True, "accepted": accepted, "rejection_reasons": reasons,
        "checkpoint": _CHECKPOINT_PATH, "device": actual_device,
        "baseline_range_5_95_deg": base_range,
        "refined_range_5_95_deg": refined_range,
        "baseline_max_step_deg": base_max,
        "refined_max_step_deg": refined_max,
        "baseline_refined_correlation": correlation,
        "lowpass_cutoff_hz": float(cutoff),
        "training": {"manual_videos": 20, "accepted_pseudo_videos": 175,
                     "held_out_manual_median_rmse_deg": 10.71,
                     "known_limitation": "Some edge-on monocular hand poses remain unresolvable."},
    }
    return (refined if accepted else baseline_relative), diagnostics
