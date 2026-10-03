"""Shared initialization for VisionMD analysis modules."""
import os

# PyTorch reads this during backend initialization. Keep it here so importing
# any app.analysis submodule enables native CPU fallback before torch loads.
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
