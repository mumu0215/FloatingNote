@echo off
setlocal EnableExtensions
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

python -m pip install pyinstaller -q
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

echo [build] Cleaning old build artifacts...
if exist "release" rmdir /s /q "release"
if exist "dist\FloatingNote" rmdir /s /q "dist\FloatingNote"
if exist "dist\FloatingNote.exe" del /f /q "dist\FloatingNote.exe"
if exist "dist\app_entry.dist" rmdir /s /q "dist\app_entry.dist"
if exist "dist\app_entry.build" rmdir /s /q "dist\app_entry.build"
if exist "build\FloatingNote" rmdir /s /q "build\FloatingNote"
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

echo [build] Packaging with PyInstaller (folder / onedir)...
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean FloatingNote.spec
if errorlevel 1 (
  echo [build] PyInstaller failed.
  exit /b 1
)

set "OUTDIR="
if exist "dist\FloatingNote\FloatingNote.exe" set "OUTDIR=dist\FloatingNote"
if "%OUTDIR%"=="" (
  echo [build] Output not found. Expected dist\FloatingNote\FloatingNote.exe
  exit /b 1
)

echo [build] Assembling release folder from %OUTDIR% ...
if exist "release\FloatingNote" rmdir /s /q "release\FloatingNote"
mkdir "release\FloatingNote"
xcopy /e /i /y /q "%OUTDIR%\*" "release\FloatingNote\" >nul
if not exist "release\FloatingNote\assets" mkdir "release\FloatingNote\assets"
if exist "assets\app.ico" copy /y "assets\app.ico" "release\FloatingNote\assets\app.ico" >nul
if exist "assets\app.png" copy /y "assets\app.png" "release\FloatingNote\assets\app.png" >nul
if not exist "release\FloatingNote\data" mkdir "release\FloatingNote\data"
echo []> "release\FloatingNote\data\notes.json.example"
> "release\FloatingNote\data\config.json.example" echo {"width":300,"height":480,"x":null,"y":null,"opacity":0.92,"autostart":true,"max_preview_chars":120,"always_on_top":true}

if exist "release\FloatingNote\FloatingNote.exe" (
  copy /y "release\FloatingNote\FloatingNote.exe" "dist\FloatingNote.exe" >nul 2>nul
)

if not exist "release\FloatingNote\FloatingNote.exe" (
  echo [build] release\FloatingNote\FloatingNote.exe missing after assemble.
  exit /b 1
)

echo.
echo [build] Done.
echo [build] Portable folder: %cd%\release\FloatingNote\
echo [build] Run: %cd%\release\FloatingNote\FloatingNote.exe
echo [build] Notes/config (persistent): %USERDATA%\
echo [build] Copy the whole FloatingNote folder anywhere - no Python needed.
echo [build] Rebuild will NOT wipe your notes (stored under LocalAppData).
endlocal
exit /b 0