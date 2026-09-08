@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [dev] Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo [dev] Failed to create venv. Is Python installed?
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"
python -m pip install -r requirements.txt -q
if errorlevel 1 (
  echo [dev] Failed to install dependencies.
  exit /b 1
)

echo [dev] Starting Floating Note...
python "src\main.py"
endlocal
