@echo off
setlocal
echo ======================================================================
echo    NotebookLM Permanent Master Token Setup
echo ======================================================================

set PYTHON_CMD=
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) else (
    set "PYTHON_CMD=py -3.12"
)

"%PYTHON_CMD%" scripts/setup_master_token.py %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo If it failed, please check your internet connection and try again.
    pause
)
