@echo off
:: SassyQueenCore Mode Control Launcher
echo SassyQueenCore Mode Control

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

:: Run the mode control utility in interactive mode
echo Launching Mode Control...
python -X utf8 mode_control.py --interactive

:END
echo.
echo Mode Control session ended.
pause 