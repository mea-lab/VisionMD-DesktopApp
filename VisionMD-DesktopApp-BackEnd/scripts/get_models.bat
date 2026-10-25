@echo off
setlocal enabledelayedexpansion

rem The inference implementation is versioned in app\analysis\models\metrabs_pytorch.
rem This script retrieves only the large, local checkpoint package it needs.
set "MODEL_URL=https://www.dropbox.com/scl/fi/nzd62nooitrh68suvau2e/metrabs_eff2l_384px_800k_28ds_pytorch.zip?rlkey=cjycmqo5c6j188jb7en1esu5i&st=t1dtf5pn&dl=1"
set "MODEL_NAME=metrabs_eff2l_384px_800k_28ds_pytorch"
set "SCRIPT_DIR=%~dp0"
set "MODEL_DIR=%SCRIPT_DIR%..\app\analysis\models"
set "TARGET_DIR=%MODEL_DIR%\%MODEL_NAME%"
set "ZIP_FILE=%MODEL_DIR%\%MODEL_NAME%.zip"

if exist "%TARGET_DIR%\ckpt.pt" (
    echo %TARGET_DIR%\ckpt.pt already exists, skipping download.
    exit /b 0
)

if not exist "%MODEL_DIR%" (
    echo Model directory %MODEL_DIR% does not exist.
    exit /b 1
)

if exist "%TARGET_DIR%" rmdir /s /q "%TARGET_DIR%"
mkdir "%TARGET_DIR%"

echo Downloading %MODEL_NAME% from Dropbox...
curl --fail --location --retry 3 "%MODEL_URL%" --output "%ZIP_FILE%"
if %errorlevel% neq 0 (
    echo Download failed.
    if exist "%ZIP_FILE%" del "%ZIP_FILE%"
    exit /b 1
)

echo Extracting checkpoint package...
powershell -NoProfile -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%TARGET_DIR%' -Force"
if %errorlevel% neq 0 (
    echo Extraction failed.
    if exist "%ZIP_FILE%" del "%ZIP_FILE%"
    rmdir /s /q "%TARGET_DIR%"
    exit /b 1
)

del "%ZIP_FILE%"
if not exist "%TARGET_DIR%\ckpt.pt" (
    echo Downloaded archive is missing ckpt.pt.
    rmdir /s /q "%TARGET_DIR%"
    exit /b 1
)

echo %MODEL_NAME% downloaded and extracted to %TARGET_DIR%
