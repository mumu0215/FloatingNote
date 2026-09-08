@echo off
setlocal
cd /d "%~dp0"

set STOPPED=0

if exist "floating_note.pid" (
  set /p PID=<floating_note.pid
  if defined PID (
    tasklist /FI "PID eq %PID%" 2>nul | find "%PID%" >nul
    if not errorlevel 1 (
      taskkill /PID %PID% /F >nul 2>&1
      if not errorlevel 1 (
        echo [stop] Stopped process PID=%PID%
        set STOPPED=1
      )
    )
  )
  del /f /q "floating_note.pid" >nul 2>&1
)

if exist "dist\floating_note.pid" (
  set /p PID=<dist\floating_note.pid
  if defined PID (
    tasklist /FI "PID eq %PID%" 2>nul | find "%PID%" >nul
    if not errorlevel 1 (
      taskkill /PID %PID% /F >nul 2>&1
      if not errorlevel 1 (
        echo [stop] Stopped process PID=%PID%
        set STOPPED=1
      )
    )
  )
  del /f /q "dist\floating_note.pid" >nul 2>&1
)

tasklist /FI "IMAGENAME eq FloatingNote.exe" 2>nul | find /I "FloatingNote.exe" >nul
if not errorlevel 1 (
  taskkill /IM FloatingNote.exe /F >nul 2>&1
  echo [stop] Stopped FloatingNote.exe
  set STOPPED=1
)

if "%STOPPED%"=="0" (
  rem Fallback: kill by command line matching main.py under this folder
  for /f "tokens=2 delims=," %%P in ('tasklist /FI "IMAGENAME eq pythonw.exe" /FO CSV /NH 2^>nul') do (
    wmic process where "ProcessId=%%~P" get CommandLine 2>nul | find /I "%~dp0src\main.py" >nul
    if not errorlevel 1 (
      taskkill /PID %%~P /F >nul 2>&1
      echo [stop] Stopped pythonw PID=%%~P
      set STOPPED=1
    )
  )
  for /f "tokens=2 delims=," %%P in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH 2^>nul') do (
    wmic process where "ProcessId=%%~P" get CommandLine 2>nul | find /I "%~dp0src\main.py" >nul
    if not errorlevel 1 (
      taskkill /PID %%~P /F >nul 2>&1
      echo [stop] Stopped python PID=%%~P
      set STOPPED=1
    )
  )
)

if "%STOPPED%"=="0" (
  echo [stop] Floating Note is not running.
) else (
  echo [stop] Done.
)
endlocal
