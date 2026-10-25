# VisionMD Desktop App Back End

This directory holds the source code for the backend of the VisionMD Desktop App. Below is documentation for developing, building and testing the backend server of VisionMD.

## Backend Overview

The backend is a Django app with these main responsibilities:

- serve API routes under `/api/`
- upload, stream, update, and delete video data
- compute bounding boxes and landmarks
- run task-specific movement analyses
- serve built frontend static assets for browser testing

Important paths:

```text
VisionMD-DesktopApp-BackEnd/app/urls.py
VisionMD-DesktopApp-BackEnd/app/views/
VisionMD-DesktopApp-BackEnd/app/analysis/
VisionMD-DesktopApp-BackEnd/app/analysis/tasks/
VisionMD-DesktopApp-BackEnd/app/analysis/detectors/
VisionMD-DesktopApp-BackEnd/app/analysis/signal_analyzers/
VisionMD-DesktopApp-BackEnd/app/analysis/models/
```

Task files in `app/analysis/tasks/` are discovered dynamically. Adding a new task file following the existing `BaseTask` pattern creates a matching API endpoint.

Current task implementations include finger tapping, hand movement, hand tremor,
leg agility, toe tapping, gait, and left/right pronation-supination analysis.

## Runtime behavior

- Task analysis is submitted through `/api/analysis_jobs/<task>/` and executed
  by one process-local worker. Serial GPU execution avoids VRAM contention while
  the UI polls job status and remains responsive.
- Expensive immutable model weights are reused within the backend process.
  Ultralytics predictor/tracker state is reset between videos so identities and
  frame geometry cannot leak from one project to another.
- Results are cached by video identity/mtime, task, and canonical parameters.
  Pass `force=1` to deliberately bypass the cache.
- Every completed task includes `analysisRuntime` telemetry and an
  `analysisQuality` badge payload (`good`, `review`, or `failed`). This is a
  technical signal-quality screen, not a clinical validity determination.
- See `app/analysis/tasks/PRONATION_SUPINATION_PIPELINE.md` for the MediaPipe
  screening, automatic WiLoR fallback, temporal correction, and limitations.

The standalone `batch_processing/batch_analyze.py` registry contains every
desktop task. It writes ordinary result JSON plus a complete
`*_visionmd_project.json` snapshot that can be imported with **Load Project
JSON** on the Home screen.

## Prerequisites
- Anaconda (or Miniconda)  
- Python 3.10

## Development
Follow the below steps to get the server running for development.

### 1. Create and Activate the Conda Environment

Use the provided `environment.yml` file to recreate the exact development environment. Make sure you use the environment according to your OS.

```bash
conda env create -f environment_{OS}.yml
conda activate VisionMD
```

### 2. Download the models
The MeTRAbs PyTorch inference implementation is part of the repository. Its
large checkpoint package is intentionally downloaded locally, rather than
stored in Git. Download it once using the script for your platform:

```bash
./scripts/get_models.sh # For Linux / MacOS
./scripts/get_models.bat # For Windows
```

The scripts create
`app/analysis/models/metrabs_eff2l_384px_800k_28ds_pytorch/`. This directory
is ignored by Git and must be present before a MeTRAbs-based analysis can run.

### 3. Start the Django Development Server

```bash
python manage.py runserver
```
You must have the backend Django server running on `127.0.0.1:8000`. After, run the frontend located at `.\VisionMD-DesktopApp-FrontEnd` Follow the instruction in the README to run the frontend for developement. After setup, the frontend will now connect to your backend.

### 4. Stop the Server
To stop the development server, press `Ctrl + C` in the terminal where the server is running.

## Testing static web assets
This documents internal testing for the VisionMD Desktop App using static web assets.

### Build and transfer the static web asssets
Follow the README in `.\VisionMD-DesktopApp-FrontEnd\README.md`. to build the static web assets. After transferring the static web assets to `.\VisionMD-DesktopApp-BackEndEnd`, rename it to `dist`.

### Start the server
```bash
python manage.py runserver
```

### Open the Application

In your browser (Chrome is recommended), navigate to:  
[http://localhost:8000/](http://localhost:8000/). The app will be available within the browser.

## Building for Production
This section documents building the Pyinstaller executable for the production installers for Windows, Linux and MacOS. The Pyinstaller executable has to be packaged with the frontend to create a proper installer.

### Building the executable
```bash
./scripts/build_windows.sh # For Windows
./scripts/build_linux.sh # For Linux
./scripts/build_mac.sh # For MacOS
```
Run the appropriate script for your OS. This will build a onedir PyInstaller executable at `./pyinstaller_builds/serve_{OS}.` Transfer this executable to `\VisionMD-DesktopApp-FrontEnd\pyinstaller_builds`. The frontend directory is now ready for building a production installer.
