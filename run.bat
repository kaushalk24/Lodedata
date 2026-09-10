@echo off
title Design Assistant
REM Double-click this file, or run it from a terminal.
REM Change the port with:  set PORT=8600 && run.bat
setlocal
if "%PORT%"=="" set PORT=8000

REM Explorer starts a double-clicked script from an arbitrary folder,
REM so move to the one holding this file before doing anything else.
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo   Python was not found.
  echo.
  echo   Install Python 3.11 or newer from https://www.python.org/downloads/
  echo   During setup, tick "Add python.exe to PATH".
  echo.
  pause
  exit /b 1
)

if not exist "app\api.py" (
  echo.
  echo   This script is not next to the app folder.
  echo   Keep run.bat in the same folder as app\, docs\ and tests\.
  echo.
  pause
  exit /b 1
)

python -c "import fastapi, uvicorn, multipart" >nul 2>nul
if errorlevel 1 (
  echo   First run - installing dependencies, this takes a minute...
  echo.
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo.
    echo   Installing dependencies failed. Try running this yourself:
    echo     python -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
  )
)

echo.
echo   Design Assistant is starting on http://127.0.0.1:%PORT%
echo   Your browser will open in a moment.
echo.
echo   Leave this window open while you work. Close it, or press Ctrl+C,
echo   to stop the program.
echo.

REM give the server a moment to bind the port, then open the browser
start "" /b cmd /c "timeout /t 3 /nobreak >nul & start """" http://127.0.0.1:%PORT%"

python -m uvicorn api:app --app-dir app --port %PORT%

echo.
echo   The program has stopped.
pause
