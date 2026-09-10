@echo off
REM Start the Design Assistant on http://127.0.0.1:8000
REM Usage:  run.bat        or   set PORT=8600 && run.bat
setlocal
if "%PORT%"=="" set PORT=8000

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found on your PATH.
  echo Install Python 3.11 or newer from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" during setup.
  exit /b 1
)

if not exist "app\api.py" (
  echo Run this from the folder that contains the app directory.
  echo   cd /d C:\path\to\Lodedata-app
  exit /b 1
)

echo Starting on http://127.0.0.1:%PORT%  -  press Ctrl+C to stop
python -m uvicorn api:app --app-dir app --reload --port %PORT%
