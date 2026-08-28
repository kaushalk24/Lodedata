@echo off
setlocal
title OpenLode Design Assistant
cd /d "%~dp0"

echo.
echo   OpenLode Design Assistant
echo   =========================
echo.

if not exist "lode\__main__.py" (
    echo   PROBLEM: this launcher is not in the OpenLode folder.
    echo.
    echo   It must sit next to the "lode" folder. Move it there, or
    echo   re-extract the download and run the copy inside.
    echo.
    echo   Currently in: %CD%
    echo.
    pause
    exit /b 1
)

set "PY="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if not defined PY (
    python --version >nul 2>&1
    if not errorlevel 1 set "PY=python"
)
if not defined PY (
    python3 --version >nul 2>&1
    if not errorlevel 1 set "PY=python3"
)

if not defined PY (
    echo   PROBLEM: Python was not found.
    echo.
    echo   Install Python 3.10 or newer from https://python.org/downloads
    echo   and tick "Add Python to PATH" during setup, then run this again.
    echo.
    pause
    exit /b 1
)

echo   Starting with: %PY%
echo   Your browser will open at http://127.0.0.1:8765
echo.
echo   Leave this window open while you work.
echo   Close it, or press Ctrl+C, to stop.
echo.

%PY% -m lode serve
set "CODE=%ERRORLEVEL%"

if not "%CODE%"=="0" (
    echo.
    echo   OpenLode stopped with error code %CODE%.
    echo   Copy the message above if you need help with it.
    echo.
    pause
)
endlocal
