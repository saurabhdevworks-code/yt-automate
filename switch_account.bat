@echo off
title Switch NotebookLM Account
cls

echo ================================================================
echo           SWITCH NOTEBOOKLM ACCOUNT FOR AUTOMATION
echo ================================================================
echo.
echo Currently available accounts on your machine:
echo.
echo   [1] bhawisyakakisan@gmail.com  (Active / 38 Notebooks)
echo   [2] saurabh.devworks@gmail.com
echo.
set /p choice="Kaunsa account use karna hai? Enter 1 or 2: "

if "%choice%"=="1" (
    py -3 scripts\switch_account.py bhawisyakakisan
) else if "%choice%"=="2" (
    py -3 scripts\switch_account.py saurabh
) else (
    echo [ERROR] Invalid choice. Please enter 1 or 2.
)

echo.
pause
