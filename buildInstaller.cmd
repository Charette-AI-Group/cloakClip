@echo off
REM Double-click this file to build the Windows installer, dist\CloakClipSetup-<version>.exe.
REM Needs Inno Setup 6:  winget install JRSoftware.InnoSetup
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Run the one-time setup first:
    echo    python -m venv .venv
    echo    .venv\Scripts\python.exe -m pip install -e ".[dev,build]"
    pause
    exit /b 1
)

".venv\Scripts\python.exe" tools\buildInstaller.py
echo.
pause
