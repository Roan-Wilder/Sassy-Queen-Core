@echo off
:: Vulkan GPU Acceleration Setup for AMD RX 580

:: Set working directory to the script's location
cd /d "%~dp0"

echo ========================================
echo SassyQueenCore Vulkan GPU Setup
echo For AMD RX 580 Graphics Card
echo ========================================
echo.
echo Working directory: %CD%
echo.

:: Check Python
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

echo.
echo This will install llama-cpp-python with Vulkan GPU support.
echo Your RX 580 supports Vulkan, making this the best GPU option.
echo.
echo Press any key to continue or Ctrl+C to cancel...
pause > nul

:: Run the Python script
python "%~dp0enable_vulkan_gpu.py"

pause
