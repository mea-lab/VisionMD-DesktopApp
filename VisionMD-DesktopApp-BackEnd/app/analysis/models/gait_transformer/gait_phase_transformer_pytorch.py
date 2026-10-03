"""PyTorch inference implementation of VisionMD's gait phase transformer.

The original model was trained with Keras and is distributed as an HDF5
weights file. This module reproduces its inference graph in PyTorch and reads
the stored arrays directly with h5py; TensorFlow is not required at runtime.
"""

import math
import os

import h5py
import numpy as np
import torch
from app.analysis.torch_device import preferred_device, run_with_device_fallback
from torch import nn
from torch.nn import functional as F


class KerasMultiHeadAttention(nn.Module):
    """Keras MHA layout where key_dim is 128 for each of three heads."""

    def __init__(self, embed_dim=128, num_heads=3, key_dim=128):
        super().__init__()
        self.key_dim = key_dim
        self.query_kernel = nn.Parameter(torch.empty(embed_dim, num_heads, key_dim))
        self.query_bias = nn.Parameter(torch.empty(num_heads, key_dim))
        self.key_kernel = nn.Parameter(torch.empty(embed_dim, num_heads, key_dim))
        self.key_bias = nn.Parameter(torch.empty(num_heads, key_dim))
        self.value_kernel = nn.Parameter(torch.empty(embed_dim, num_heads, key_dim))
        self.value_bias = nn.Parameter(torch.empty(num_heads, key_dim))
        self.output_kernel = nn.Parameter(torch.empty(num_heads, key_dim, embed_dim))
        self.output_bias = nn.Parameter(torch.empty(embed_dim))

    def forward(self, query, key, value):
        q = torch.einsum("bte,ehd->bthd", query, self.query_kernel) + self.query_bias
        k = torch.einsum("bse,ehd->bshd", key, self.key_kernel) + self.key_bias
        v = torch.einsum("bse,ehd->bshd", value, self.value_kernel) + self.value_bias
        scores = torch.einsum("bthd,bshd->bhts", q, k) / math.sqrt(self.key_dim)
        attention = torch.softmax(scores, dim=-1)
        context = torch.einsum("bhts,bshd->bthd", attention, v)
        return torch.einsum("bthd,hde->bte", context, self.output_kernel) + self.output_bias


class EncoderLayer(nn.Module):
    def __init__(self, shared_attention):
        super().__init__()
        self.attention = shared_attention
        self.linear1 = nn.Linear(128, 256)
        self.linear2 = nn.Linear(256, 128)
        self.norm1 = nn.LayerNorm(128, eps=1e-6)
        self.norm2 = nn.LayerNorm(128, eps=1e-6)

    def forward(self, value, positional_encoding):
        query_key = value + positional_encoding
        value = self.norm1(value + self.attention(query_key, query_key, value))
        feed_forward = self.linear2(F.gelu(self.linear1(value), approximate="none"))
        return self.norm2(value + feed_forward)


class GaitPhaseStrideTransformer(nn.Module):
    KP_INDICES = (0, 1, 2, 3, 4, 5, 6, 11, 12, 13, 14, 15, 16)

    def __init__(self, pos_divider=None):
        super().__init__()
        self.pos_divider = pos_divider
        self.demographics_embedding = nn.Linear(1, 128)
        self.pose_embedding = nn.Linear(39, 128)
        self.shared_attention = KerasMultiHeadAttention()
        self.encoder_layers = nn.ModuleList([
            EncoderLayer(self.shared_attention) for _ in range(6)
        ])
        self.head1 = nn.Linear(128, 256)
        self.head2 = nn.Linear(256, 256)
        self.output = nn.Linear(256, 19)

        # The original Keras graph created these ten embeddings as an
        # untracked construction-time constant, so they are absent from the
        # HDF5 weights. Use a fixed seed to retain that behavior reproducibly.
        generator = torch.Generator().manual_seed(20260920)
        self.register_buffer(
            "demographic_positions",
            torch.empty(10, 128).uniform_(-0.05, 0.05, generator=generator),
        )

    def _pose_positions(self, length, dtype, device):
        positions = torch.arange(length, dtype=dtype, device=device)
        if self.pos_divider is not None:
            positions = positions / self.pos_divider
        exponents = torch.linspace(0, 1, 64, dtype=dtype, device=device)
        rates = torch.pow(torch.tensor(1.0 / 10000.0, dtype=dtype, device=device), exponents)
        angles = positions[:, None] * rates[None, :]
        return torch.cat([torch.sin(angles), torch.cos(angles)], dim=-1)

    def forward(self, inputs, training=False):
        keypoints, height = inputs
        device = next(self.parameters()).device
        keypoints = torch.as_tensor(keypoints, dtype=torch.float32, device=device)
        height = torch.as_tensor(height, dtype=torch.float32, device=device).reshape(-1, 1, 1)
        keypoints = keypoints[:, :, self.KP_INDICES, :]
        poses = self.pose_embedding(keypoints.flatten(start_dim=2))
        demographics = self.demographics_embedding(height).expand(-1, 10, -1)
        encoded = torch.cat([demographics, poses], dim=1)

        pose_positions = self._pose_positions(poses.shape[1], poses.dtype, poses.device)
        positions = torch.cat([
            self.demographic_positions.to(dtype=poses.dtype, device=poses.device),
            pose_positions,
        ], dim=0).unsqueeze(0)
        for layer in self.encoder_layers:
            encoded = layer(encoded, positions)

        result = self.output(F.gelu(self.head2(F.gelu(self.head1(encoded), approximate="none")), approximate="none"))
        return result[:, 10:, :, None]


def _copy_linear(layer, group):
    layer.weight.data.copy_(torch.from_numpy(group["kernel:0"][...].T))
    layer.bias.data.copy_(torch.from_numpy(group["bias:0"][...]))


def _copy_layer_norm(layer, group):
    layer.weight.data.copy_(torch.from_numpy(group["gamma:0"][...]))
    layer.bias.data.copy_(torch.from_numpy(group["beta:0"][...]))


def _load_keras_weights(model, model_file):
    with h5py.File(model_file, "r") as weights:
        _copy_linear(model.demographics_embedding, weights["demographics_embedding/demographics_embedding"])
        _copy_linear(model.pose_embedding, weights["embedding/embedding"])
        _copy_linear(model.head1, weights["dense_15/dense_15"])
        _copy_linear(model.head2, weights["dense_16/dense_16"])
        _copy_linear(model.output, weights["dense_17/dense_17"])

        attention_group = weights[
            "encoder_transformer_layer_30/encoder_transformer_layer_30/"
            "multi_head_attention_5"
        ]
        attention = model.shared_attention
        for name in ("query", "key", "value"):
            source = attention_group[name]
            getattr(attention, f"{name}_kernel").data.copy_(torch.from_numpy(source["kernel:0"][...]))
            getattr(attention, f"{name}_bias").data.copy_(torch.from_numpy(source["bias:0"][...]))
        attention.output_kernel.data.copy_(torch.from_numpy(attention_group["attention_output/kernel:0"][...]))
        attention.output_bias.data.copy_(torch.from_numpy(attention_group["attention_output/bias:0"][...]))

        for offset, layer in enumerate(model.encoder_layers):
            layer_name = f"encoder_transformer_layer_{30 + offset}"
            group = weights[layer_name]
            _copy_linear(layer.linear1, group["dense"])
            _copy_linear(layer.linear2, group["dense_1"])
            norm_root = group[layer_name]
            _copy_layer_norm(layer.norm1, norm_root[f"layer_normalization_{60 + 2 * offset}"])
            _copy_layer_norm(layer.norm2, norm_root[f"layer_normalization_{61 + 2 * offset}"])


def load_default_model(pos_divider=None, device=None):
    model_file = os.path.join(os.path.dirname(__file__), "assets", "model_v0.2.h5")
    selected = preferred_device(device)

    def load_on(active_device):
        model = GaitPhaseStrideTransformer(pos_divider=pos_divider)
        _load_keras_weights(model, model_file)
        return model.eval().to(active_device)

    model, _actual_device = run_with_device_fallback(
        load_on, selected, label="gait transformer initialization"
    )
    return model


def shift_generator(keypoints3d, stride=1, L=90):
    length_indices = np.arange(L)
    for start in np.arange(0, keypoints3d.shape[0] - L + 1, stride):
        yield keypoints3d[length_indices + start]


def chunk_generator(keypoints3d, stride=1, L=90, batch_size=32):
    samples = shift_generator(keypoints3d, stride=stride, L=L)
    while True:
        chunk = []
        try:
            for _ in range(batch_size):
                chunk.append(next(samples))
        except StopIteration:
            pass
        if not chunk:
            break
        yield np.asarray(chunk)


def gait_phase_stride_inference(keypoints3d, height, regressor, L, batch_size=128):
    with torch.inference_mode():
        if keypoints3d.shape[0] >= L:
            offset = (L - 1) // 2
            predictions = []
            for chunk in chunk_generator(keypoints3d, L=L, batch_size=batch_size):
                chunk_height = height / 1000.0 * np.ones((chunk.shape[0],), dtype=np.float32)
                predictions.append(regressor((chunk, chunk_height))[..., 0].cpu().numpy())
            predictions = np.concatenate(predictions, axis=0)
            phases = np.concatenate([
                predictions[0, :offset], predictions[:, offset], predictions[-1, offset + 1:],
            ], axis=0)
        else:
            phases = regressor((
                keypoints3d[None, ...], np.asarray(height, dtype=np.float32)[None] / 1000.0,
            ))[0, ..., 0].cpu().numpy()
    return phases[:, :8], phases[:, 8:]
