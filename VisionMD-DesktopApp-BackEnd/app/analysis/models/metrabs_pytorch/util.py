"""Inference-only configuration helper for the vendored MeTRAbs port.

The upstream repository uses Hydra, posepile and simplepyutils to configure
training. VisionMD only loads an exported checkpoint, so the desktop inference
path intentionally supports a single compact YAML configuration.
"""

from pathlib import Path
from types import SimpleNamespace

import yaml


_config = None


def load_config(config_path):
    global _config
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as stream:
        values = yaml.safe_load(stream) or {}
    defaults = {
        "regularize_to_manifold": False,
        "rot_aug_360": False,
        "rot_aug_360_half": False,
        "rot_aug": 25,
    }
    defaults.update(values)
    _config = SimpleNamespace(**defaults)
    return _config


def get_config(config_path=None):
    if config_path is not None:
        return load_config(config_path)
    if _config is None:
        raise RuntimeError("MeTRAbs configuration has not been loaded")
    return _config
