@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File run_local_pipeline.ps1
pause
