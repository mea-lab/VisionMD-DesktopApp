@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0get_models.ps1" %*
exit /b %errorlevel%
