@echo off
rem Builds dist\LodeData\LodeData.exe, the Design Assistant as a Windows
rem program, and checks it. Needs Python 3.10 or newer on PATH (Windows).
cd /d "%~dp0\.."
python -m pip install -r requirements.txt -r desktop\requirements.txt || exit /b 1
python -m PyInstaller --noconfirm --clean --windowed --name LodeData ^
  --paths app --paths tools --add-data "app\web;web" ^
  --collect-all webview --collect-submodules uvicorn ^
  --hidden-import python_multipart --hidden-import multipart ^
  desktop\lodedata_desktop.py || exit /b 1
copy /y desktop\LodeData.exe.config dist\LodeData\ >nul || exit /b 1
del lodedata-check.log 2>nul
start "" /wait dist\LodeData\LodeData.exe --check
if %errorlevel% neq 0 (type lodedata-check.log & echo LodeData.exe failed its check & exit /b 1)
findstr /c:"check passed" lodedata-check.log >nul || (echo LodeData.exe did not finish its check & exit /b 1)
echo Built and checked: dist\LodeData\LodeData.exe
