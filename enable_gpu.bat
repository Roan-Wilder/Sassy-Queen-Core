@echo off
:: SassyQueenCore GPU Acceleration Setup
echo SassyQueenCore GPU Acceleration Setup for AMD RX590

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

:: Install required packages
echo Installing required packages...
pip install requests wmi

:: Run the GPU acceleration setup script
echo Running GPU acceleration setup...
python enable_gpu.py

:END
echo.
echo Setup completed.
pause 