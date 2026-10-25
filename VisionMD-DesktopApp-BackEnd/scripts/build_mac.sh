./scripts/get_models.sh

pyinstaller serve_mac.py \
  --console \
  --onedir  \
  --distpath ./pyinstaller_builds \
  --add-data "VideoAnalysisToolBackend:VideoAnalysisToolBackend" \
  --add-data "app:app" \
  --add-data "mime.types:mime.types" \
  --clean \
  --noconfirm \
  --collect-all numpy \
  --collect-all scipy \
  --collect-all h5py \
  --collect-all torch \
  --collect-all torchvision \
  --collect-all opencv-python \
  --collect-all pandas \
  --add-binary "$CONDA_PREFIX/bin/ffmpeg:." \
  --add-binary "$CONDA_PREFIX/bin/ffprobe:." \
  --hidden-import=scipy._lib.array_api_compat.numpy.fft \
  --noconfirm \
