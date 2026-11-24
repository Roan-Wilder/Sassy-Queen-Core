@echo off
:: SassyQueenCore Database Unlock Utility
echo SassyQueenCore Database Unlock Utility

:: Set base directory to script location
set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

:: Set UTF-8 code page for Windows
chcp 65001 > nul
echo UTF-8 encoding enabled.

:: Set Python environment variables for UTF-8
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

:: Check Python installation
echo Checking Python installation...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found or not in PATH.
    goto END
)

:: Make sure no SassyQueenCore processes are running
echo.
echo Checking for running SassyQueenCore processes...
tasklist /fi "IMAGENAME eq python.exe" | find /i "python.exe" > nul
if %ERRORLEVEL% EQU 0 (
    echo.
    echo WARNING: Python processes are still running.
    echo          These might be holding database locks.
    echo.
    set /p close_processes="Would you like to attempt to close Python processes? (y/n): "
    if /i "%close_processes%"=="y" (
        echo.
        echo Attempting to close Python processes...
        taskkill /f /im python.exe > nul 2>&1
        if %ERRORLEVEL% EQU 0 (
            echo Successfully closed Python processes.
        ) else (
            echo Failed to close some Python processes.
            echo Try closing SassyQueenCore manually before proceeding.
        )
    )
)

:: Wait a moment for processes to fully close
timeout /t 2 > nul

:: Run the database unlock utility
echo.
echo Running database unlock utility...
python -X utf8 db_unlock.py

:END
echo.
echo Database unlock process completed.
pause 