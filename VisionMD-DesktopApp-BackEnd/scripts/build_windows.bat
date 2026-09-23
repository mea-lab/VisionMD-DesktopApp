@echo off
setlocal enabledelayedexpansion

call scripts\get_models.bat
if %errorlevel% neq 0 exit /b %errorlevel%

pyinstaller serve_windows.py ^
  --console ^
  --onedir ^
  --distpath ./pyinstaller_builds ^
  --add-data "VideoAnalysisToolBackend;VideoAnalysisToolBackend" ^
  --add-data "app;app" ^
  --clean ^
  --noconfirm ^
  --collect-all numpy ^
  --collect-all scipy ^
  --collect-all h5py ^
  --collect-all torch ^
  --collect-all torchvision ^
  --collect-all opencv-python ^
  --collect-all pandas ^
  --add-binary "%CONDA_PREFIX%\Library\bin\ffmpeg.exe;." ^
  --add-binary "%CONDA_PREFIX%\Library\bin\ffprobe.exe;." ^
  --hidden-import=scipy._lib.array_api_compat.numpy.fft
