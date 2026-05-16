# VisionMD Desktop App

VisionMD is a cross-platform desktop application for video-based kinematic analysis of motor tasks. The app combines an React frontend with a Django backend inside an Electron runtime that processes videos, extracts landmarks, analyzes task-specific signals, and displays plots and metrics for the user.

This repository splits the application into two main parts:

- `VisionMD-DesktopApp-FrontEnd/` - Manages video review, task selection, visualizations and cross-platform installer builds.
- `VisionMD-DesktopApp-BackEnd/` - Manages video data management, landmark detection, task analysis, signal analysis, and PyInstaller builds.

The rest of this document goes over the development, testing and deployment of VisionMD. Depending on your platform, some steps may vary.

## Minimum Prerequisites

- Conda or Miniconda
- Python 3.10
- Node.js and npm

## Development Setup
1. Setup the backend Django server using the instructions in VisionMD-DesktopApp-BackEnd\README.md.
2. Setup the Electron renderer using the instructions in VisionMD-DesktopApp-FrontEnd\README.md.

## Production Setup
1. Build the backend Pyinstaller executable using the instructions in VisionMD-DesktopApp-BackEnd\README.md.
2. Transfer the Pyinstaller executable to the frontend.
3. Build the frontend installers depending on your OS using the instructions in VisionMD-DesktopApp-FrontEnd\README.md.

## Static Testing Setup
1. Follow the instructions in VisionMD-DesktopApp-FrontEnd\README.md to build the static web assets.
2. Follow the instructions in VisionMD-DesktopApp-BackEnd\README.md to move the static web assets and run the server.

If you simply want to test the static version of VisionMD, simply run `./VisionMD-DesktopApp-BackEnd/manage.py runserver` with the correct Conda environment activated.