@echo off
REM Double-click this file to build the standalone dist\CloakClip.exe.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Run the one-time setup first:
    echo    python -m venv .venv
    echo    .venv\Scripts\python.exe -m pip install -e ".[dev,build]"
    pause
    exit /b 1
)

".venv\Scripts\python.exe" tools\buildStandalone.py
echo.
pause
