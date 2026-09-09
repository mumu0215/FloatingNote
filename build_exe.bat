@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

REM Unbuffered Python so build_log.txt is complete if the process crashes.
set "PYTHONUNBUFFERED=1"
set "PYTHONIOENCODING=utf-8"

echo [build] Preparing virtual environment...
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 (
    echo [build] Failed to create venv. Is Python installed?
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"
python -m pip install -r requirements.txt -q
if errorlevel 1 (
  echo [build] Failed to install app dependencies.
  exit /b 1
)

python -m pip install "pyinstaller>=6.14" -q
if errorlevel 1 (
  echo [build] Failed to install PyInstaller.
  exit /b 1
)

echo [build] Backing up notes/config to %%LOCALAPPDATA%%\FloatingNote ...
set "USERDATA=%LOCALAPPDATA%\FloatingNote"
if not exist "%USERDATA%" mkdir "%USERDATA%"
if not exist "%USERDATA%\notes.json" (
  if exist "release\FloatingNote\data\notes.json" (
    copy /y "release\FloatingNote\data\notes.json" "%USERDATA%\notes.json" >nul
  ) else if exist "data\notes.json" (
    copy /y "data\notes.json" "%USERDATA%\notes.json" >nul
  )
)
if not exist "%USERDATA%\config.json" (
  if exist "release\FloatingNote\data\config.json" (
    copy /y "release\FloatingNote\data\config.json" "%USERDATA%\config.json" >nul
  ) else if exist "data\config.json" (
    copy /y "data\config.json" "%USERDATA%\config.json" >nul
  )
)

echo [build] Cleaning old build workdirs (release kept until success)...
if exist "dist\FloatingNote" rmdir /s /q "dist\FloatingNote"
if exist "dist\FloatingNote.exe" del /f /q "dist\FloatingNote.exe"
if exist "dist\app_entry.dist" rmdir /s /q "dist\app_entry.dist"
if exist "dist\app_entry.build" rmdir /s /q "dist\app_entry.build"
if exist "build\FloatingNote" rmdir /s /q "build\FloatingNote"
if exist "%LOCALAPPDATA%\pyinstaller" rmdir /s /q "%LOCALAPPDATA%\pyinstaller" 2>nul
if not exist "dist" mkdir "dist"
if not exist "release" mkdir "release"
if not exist "assets" mkdir "assets"

echo [build] Ensuring app icon...
.\.venv\Scripts\python.exe "scripts\gen_app_icon.py"
if errorlevel 1 (
  echo [build] Failed to generate assets\app.ico
  exit /b 1
)
if not exist "assets\app.ico" (
  echo [build] assets\app.ico still missing
  exit /b 1
)

set "OUTDIR=dist\FloatingNote"
set "MAX_TRY=3"
set "TRY=1"
set "BUILD_OK=0"

:build_try
echo [build] Packaging with PyInstaller (folder / onedir) attempt !TRY!/!MAX_TRY! ...
if exist "dist\FloatingNote" rmdir /s /q "dist\FloatingNote"
if exist "build\FloatingNote" rmdir /s /q "build\FloatingNote"
if exist "build_log.txt" del /f /q "build_log.txt"
REM Drop stale bytecode caches that can confuse PyInstaller+Python3.13 dis()
if exist "src\__pycache__" rmdir /s /q "src\__pycache__"
if exist "__pycache__" rmdir /s /q "__pycache__"

.\.venv\Scripts\python.exe -u -m PyInstaller --noconfirm --clean FloatingNote.spec > build_log.txt 2>&1
set "PI_RC=!ERRORLEVEL!"

if exist "%OUTDIR%\FloatingNote.exe" if exist "%OUTDIR%\_internal\python313.dll" if exist "%OUTDIR%\_internal\base_library.zip" (
  set "BUILD_OK=1"
  goto build_done
)

echo [build] Attempt !TRY! failed ^(exit=!PI_RC!^).
if exist "build_log.txt" (
  echo [build] ---- last 30 lines of build_log.txt ----
  powershell -NoProfile -Command "Get-Content -Path 'build_log.txt' -Tail 30 -ErrorAction SilentlyContinue"
  echo [build] ----------------------------------------
)

if !TRY! geq !MAX_TRY! goto build_failed
set /a TRY+=1
echo [build] Retrying after clearing PyInstaller cache...
if exist "%LOCALAPPDATA%\pyinstaller" rmdir /s /q "%LOCALAPPDATA%\pyinstaller" 2>nul
goto build_try

:build_failed
echo [build] PyInstaller failed after !MAX_TRY! attempts. See build_log.txt
echo [build] Previous release\ folder was NOT overwritten.
exit /b 1

:build_done
if not "!PI_RC!"=="0" (
  echo [build] WARNING: PyInstaller exit code=!PI_RC! but required outputs exist; continuing.
)

echo [build] Verifying runtime payload in %OUTDIR% ...
if not exist "%OUTDIR%\_internal\python313.dll" (
  echo [build] ERROR: missing %OUTDIR%\_internal\python313.dll
  exit /b 1
)
if not exist "%OUTDIR%\_internal\base_library.zip" (
  echo [build] ERROR: missing %OUTDIR%\_internal\base_library.zip
  echo [build] This causes: Failed to start embedded Python interpreter
  exit /b 1
)
if not exist "%OUTDIR%\_internal\VCRUNTIME140.dll" (
  echo [build] ERROR: missing %OUTDIR%\_internal\VCRUNTIME140.dll
  exit /b 1
)

echo [build] Assembling release folder from %OUTDIR% ...
if exist "release\FloatingNote" rmdir /s /q "release\FloatingNote"
mkdir "release\FloatingNote"
xcopy /e /i /y /q "%OUTDIR%\*" "release\FloatingNote\" >nul
if errorlevel 1 (
  echo [build] Failed to copy build output to release\
  exit /b 1
)
if not exist "release\FloatingNote\assets" mkdir "release\FloatingNote\assets"
if exist "assets\app.ico" copy /y "assets\app.ico" "release\FloatingNote\assets\app.ico" >nul
if exist "assets\app.png" copy /y "assets\app.png" "release\FloatingNote\assets\app.png" >nul
if not exist "release\FloatingNote\data" mkdir "release\FloatingNote\data"
echo []> "release\FloatingNote\data\notes.json.example"
> "release\FloatingNote\data\config.json.example" echo {"width":300,"height":480,"x":null,"y":null,"opacity":0.92,"autostart":true,"max_preview_chars":120,"always_on_top":true}

REM Do NOT copy a lone FloatingNote.exe outside the folder.
REM onedir packages MUST keep exe next to _internal\ or you get:
REM   "Failed to start embedded Python interpreter"

if not exist "release\FloatingNote\FloatingNote.exe" (
  echo [build] release\FloatingNote\FloatingNote.exe missing after assemble.
  exit /b 1
)
if not exist "release\FloatingNote\_internal\python313.dll" (
  echo [build] release\_internal\python313.dll missing after assemble.
  exit /b 1
)
if not exist "release\FloatingNote\_internal\base_library.zip" (
  echo [build] release\_internal\base_library.zip missing after assemble.
  exit /b 1
)

echo.
echo [build] Done.
echo [build] Portable folder: %cd%\release\FloatingNote\
echo [build] Run: %cd%\release\FloatingNote\FloatingNote.exe
echo [build] Notes/config (persistent): %USERDATA%\
echo [build] IMPORTANT: copy the WHOLE FloatingNote folder (exe + _internal).
echo [build] Running only the .exe without _internal will fail to start.
echo [build] Rebuild will NOT wipe your notes (stored under LocalAppData).
endlocal
exit /b 0
