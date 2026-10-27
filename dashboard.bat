@echo off
setlocal
echo ======================================================================
echo    Launching YouTube Automation Studio Dashboard...
echo ======================================================================

set PYTHON_CMD=
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) else (
    set "PYTHON_CMD=py -3.12"
)

"%PYTHON_CMD%" scripts/dashboard.py
pause
