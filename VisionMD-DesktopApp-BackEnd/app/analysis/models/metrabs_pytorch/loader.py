"""VisionMD loader for the inference-only PyTorch MeTRAbs model."""

import pickle
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import torch

from .backbones import efficientnet as efficientnet_pt
from .joint_info import JointInfo
from .models.metrabs import Metrabs
from .multiperson.multiperson_model import Pose3dEstimator
from .util import load_config

_MODEL_CACHE = {}
MODEL_DOWNLOAD_URL = (
    "https://www.dropbox.com/scl/fi/nzd62nooitrh68suvau2e/"
    "metrabs_eff2l_384px_800k_28ds_pytorch.zip"
    "?rlkey=cjycmqo5c6j188jb7en1esu5i&st=t1dtf5pn&dl=1"
)
REQUIRED_MODEL_FILES = (
    "ckpt.pt", "config.yaml", "joint_info.npz",
    "joint_transform_matrix.npy", "skeleton_infos.pkl",
)


def _download_model(model_dir):
    """Download the ignored checkpoint package on first use.

    Extraction happens in a temporary sibling directory and is moved into
    place only after every required file has been verified. Packaged builds
    call get_models before PyInstaller and therefore normally bundle it.
    """
    if model_dir.exists():
        raise FileNotFoundError(
            f"PyTorch MeTRAbs model directory is incomplete at {model_dir}. "
            "Remove the incomplete directory and run scripts/get_models.sh "
            "(or get_models.bat on Windows)."
        )
    model_dir.parent.mkdir(parents=True, exist_ok=True)
    print("PyTorch MeTRAbs checkpoint is missing; downloading it from Dropbox...")
    with tempfile.TemporaryDirectory(prefix="metrabs-download-", dir=model_dir.parent) as temp_name:
        temp_dir = Path(temp_name)
        archive_path = temp_dir / "model.zip"
        extract_dir = temp_dir / "model"
        extract_dir.mkdir()
        urllib.request.urlretrieve(MODEL_DOWNLOAD_URL, archive_path)
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                destination = (extract_dir / member.filename).resolve()
                if extract_dir.resolve() not in destination.parents and destination != extract_dir.resolve():
                    raise RuntimeError("Unsafe path found in MeTRAbs model archive")
            archive.extractall(extract_dir)
        missing = [name for name in REQUIRED_MODEL_FILES if not (extract_dir / name).is_file()]
        if missing:
            raise RuntimeError(f"Downloaded MeTRAbs archive is missing: {', '.join(missing)}")
        extract_dir.replace(model_dir)
    print(f"PyTorch MeTRAbs checkpoint downloaded to {model_dir}")


def load_model(model_dir, device=None):
    model_dir = Path(model_dir)
    missing = [name for name in REQUIRED_MODEL_FILES if not (model_dir / name).is_file()]
    if missing:
        _download_model(model_dir)

    device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    cache_key = (str(model_dir.resolve()), str(device))
    if cache_key in _MODEL_CACHE:
        return _MODEL_CACHE[cache_key]
    config = load_config(model_dir / "config.yaml")
    joint_data = np.load(model_dir / "joint_info.npz")
    joint_info = JointInfo(joint_data["joint_names"], joint_data["joint_edges"])

    backbone_factory = getattr(efficientnet_pt, f"efficientnet_v2_{config.efficientnet_size}")
    with torch.device(device):
        backbone_raw = backbone_factory()
        backbone = torch.nn.Sequential(efficientnet_pt.PreprocLayer(), backbone_raw.features)
        crop_model = Metrabs(backbone, joint_info)
        crop_model((
            torch.zeros((1, 3, config.proc_side, config.proc_side), dtype=torch.float32),
            torch.eye(3, dtype=torch.float32).unsqueeze(0),
        ))

    state = torch.load(model_dir / "ckpt.pt", map_location=device, weights_only=True)
    crop_model.load_state_dict(state)
    crop_model.eval().to(device)

    with (model_dir / "skeleton_infos.pkl").open("rb") as stream:
        skeleton_infos = pickle.load(stream)
    joint_transform = np.load(model_dir / "joint_transform_matrix.npy")

    with torch.device(device):
        estimator = Pose3dEstimator(crop_model, skeleton_infos, joint_transform)
    estimator.eval().to(device)
    estimator.device = device
    _MODEL_CACHE[cache_key] = estimator
    return estimator
