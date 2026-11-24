@echo off
:: SassyQueenCore Plugin Path Fix Script
echo SassyQueenCore Plugin Path Fix

:: Set base directory
set BASE_DIR=%~dp0
cd %BASE_DIR%

:: Set UTF-8 code page for Windows
chcp 65001 > nul
echo UTF-8 encoding enabled.

:: Check Python installation
echo Checking Python installation...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found or not in PATH.
    goto END
)

:: Run the Python plugin fix script
echo Running plugin fix script...
python fix_plugins.py

:END
echo.
echo If plugins were fixed successfully, try running the launch_fix.bat script.
pause 