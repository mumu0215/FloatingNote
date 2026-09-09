@echo off
setlocal
cd /d "%~dp0"

set "USER_PID=%LOCALAPPDATA%\FloatingNote\floating_note.pid"
if exist "%USER_PID%" (
  set /p OLD_PID=<"%USER_PID%"
  if defined OLD_PID (
    tasklist /FI "PID eq %OLD_PID%" 2>nul | find "%OLD_PID%" >nul
    if not errorlevel 1 (
      echo [start] Floating Note is already running. PID=%OLD_PID%
      exit /b 0
    )
  )
)
if exist "floating_note.pid" (
  set /p OLD_PID=<floating_note.pid
  if defined OLD_PID (
    tasklist /FI "PID eq %OLD_PID%" 2>nul | find "%OLD_PID%" >nul
    if not errorlevel 1 (
      echo [start] Floating Note is already running. PID=%OLD_PID%
      exit /b 0
    )
  )
)

rem Prefer packaged portable release if present
if exist "release\FloatingNote\FloatingNote.exe" (
  start "" /D "release\FloatingNote" "release\FloatingNote\FloatingNote.exe"
  echo [start] Floating Note started (portable exe).
  exit /b 0
)
if exist "dist\FloatingNote.exe" (
  start "" "dist\FloatingNote.exe"
  echo [start] Floating Note started (exe).
  exit /b 0
)
if exist "FloatingNote.exe" (
  start "" "FloatingNote.exe"
  echo [start] Floating Note started (exe).
  exit /b 0
)

if not exist ".venv\Scripts\pythonw.exe" (
  if not exist ".venv\Scripts\python.exe" (
    echo [start] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
      echo [start] Failed to create venv.
      exit /b 1
    )
  )
  call ".venv\Scripts\activate.bat"
  python -m pip install -r requirements.txt -q
  if errorlevel 1 (
    echo [start] Failed to install dependencies.
    exit /b 1
  )
)

if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" "src\main.py"
) else (
  start "" ".venv\Scripts\python.exe" "src\main.py"
)

echo [start] Floating Note started.
endlocal
