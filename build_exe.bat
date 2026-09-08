@echo off
setlocal
cd /d "%~dp0"

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

python -m pip install nuitka ordered-set zstandard -q
if errorlevel 1 (
  echo [build] Failed to install Nuitka.
  exit /b 1
)

echo [build] Cleaning old build artifacts...
if exist "release" rmdir /s /q "release"
if exist "dist\FloatingNote.exe" del /f /q "dist\FloatingNote.exe"
if exist "dist\FloatingNote.dist" rmdir /s /q "dist\FloatingNote.dist"
if exist "dist\app_entry.build" rmdir /s /q "dist\app_entry.build"
if exist "dist\app_entry.dist" rmdir /s /q "dist\app_entry.dist"
if exist "dist\app_entry.onefile-build" rmdir /s /q "dist\app_entry.onefile-build"
if not exist "dist" mkdir "dist"
if not exist "release" mkdir "release"

echo [build] Packaging with Nuitka standalone folder (may take several minutes)...
.\.venv\Scripts\python.exe -m nuitka --standalone --windows-console-mode=disable --enable-plugin=tk-inter --include-package=src --include-module=pystray --include-module=PIL --nofollow-import-to=PIL.ImageQt --output-dir=dist --output-filename=FloatingNote.exe --assume-yes-for-downloads --remove-output app_entry.py
if errorlevel 1 (
  echo [build] Nuitka failed.
  exit /b 1
)

rem Nuitka standalone output is typically dist\app_entry.dist\
set "OUTDIR="
if exist "dist\app_entry.dist\FloatingNote.exe" set "OUTDIR=dist\app_entry.dist"
if exist "dist\FloatingNote.dist\FloatingNote.exe" set "OUTDIR=dist\FloatingNote.dist"
if exist "dist\FloatingNote.exe" set "OUTDIR=dist"

if "%OUTDIR%"=="" (
  echo [build] Output not found.
  exit /b 1
)

echo [build] Assembling release folder...
if exist "release\FloatingNote" rmdir /s /q "release\FloatingNote"
mkdir "release\FloatingNote"
xcopy /e /i /y /q "%OUTDIR%\*" "release\FloatingNote\" >nul
if not exist "release\FloatingNote\data" mkdir "release\FloatingNote\data"
if exist "data\notes.json" copy /y "data\notes.json" "release\FloatingNote\data\notes.json" >nul
if exist "data\config.json" copy /y "data\config.json" "release\FloatingNote\data\config.json" >nul
if not exist "release\FloatingNote\data\notes.json" echo []> "release\FloatingNote\data\notes.json"
if not exist "release\FloatingNote\data\config.json" (
  echo {"width":300,"height":480,"x":null,"y":null,"opacity":0.92,"autostart":true,"max_preview_chars":120,"always_on_top":true}> "release\FloatingNote\data\config.json"
)

rem Also place a convenience copy at dist\FloatingNote.exe when onefile-like single folder
if exist "release\FloatingNote\FloatingNote.exe" (
  copy /y "release\FloatingNote\FloatingNote.exe" "dist\FloatingNote.exe" >nul 2>nul
)

echo.
echo [build] Done.
echo [build] Portable folder: %cd%\release\FloatingNote\
echo [build] Run: %cd%\release\FloatingNote\FloatingNote.exe
echo [build] Copy the whole FloatingNote folder anywhere - no Python needed.
endlocal
