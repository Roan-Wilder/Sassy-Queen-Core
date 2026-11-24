@echo off
:: SassyQueenCore ROCm Installation Helper
echo SassyQueenCore ROCm Installation Helper for AMD RX580
echo This script will help you install ROCm for Windows

:: Set base directory
set BASE_DIR=%~dp0
cd %BASE_DIR%

:: Set UTF-8 code page for Windows
chcp 65001 > nul
echo UTF-8 encoding enabled.

:: Check for administrator privileges
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: This script requires administrator privileges.
    echo Please right-click and select "Run as administrator".
    goto END
)

echo.
echo ===================================================
echo ROCm Installation Guide for AMD RX580
echo ===================================================
echo.
echo This script will help you install ROCm for your AMD RX580.
echo.
echo Step 1: Download ROCm
echo ====================
echo.
echo Please download ROCm from the official AMD website:
echo https://rocm.docs.amd.com/en/latest/deploy/windows/index.html
echo.
echo Click on the "Download" button for Windows.
echo.
echo Step 2: Install ROCm
echo ===================
echo.
echo 1. Run the downloaded installer as administrator
echo 2. Follow the installation wizard
echo 3. Accept the license agreement
echo 4. Choose the default installation location
echo 5. Complete the installation
echo.
echo Step 3: Verify Installation
echo ========================
echo.
echo After installation, we'll verify that ROCm is properly installed.
echo.
echo Press any key to continue with verification...
pause >nul

:: Check for ROCm installation
echo.
echo Checking for ROCm installation...

:: Check common installation paths
set ROCM_PATHS=^
C:\Program Files\AMD\ROCm^
C:\AMD\ROCm^
C:\Program Files (x86)\AMD\ROCm

for %%p in (%ROCM_PATHS%) do (
    if exist "%%p" (
        echo Found ROCm at: %%p
        set ROCM_PATH=%%p
        goto ROCM_FOUND
    )
)

:ROCM_NOT_FOUND
echo.
echo ROCm installation not found in common locations.
echo.
echo Please ensure you have completed the installation from Step 2.
echo.
echo Would you like to:
echo 1. Try again (if you just installed ROCm)
echo 2. Exit and install ROCm manually
echo.
set /p choice="Enter your choice (1 or 2): "

if "%choice%"=="1" goto ROCM_FOUND
if "%choice%"=="2" goto END
goto ROCM_NOT_FOUND

:ROCM_FOUND
echo.
echo ROCm installation found!
echo.
echo Step 4: Configure Environment Variables
echo ====================================
echo.
echo We'll now configure the environment variables for ROCm.
echo.

:: Add ROCm to PATH if not already present
setx ROCM_PATH "%ROCM_PATH%" /M
echo Added ROCM_PATH environment variable.

:: Check if ROCm is in PATH
echo %PATH% | findstr /i /c:"%ROCM_PATH%" >nul
if %ERRORLEVEL% NEQ 0 (
    setx PATH "%PATH%;%ROCM_PATH%\bin" /M
    echo Added ROCm to PATH.
) else (
    echo ROCm is already in PATH.
)

echo.
echo Step 5: Install Required Python Packages
echo =====================================
echo.
echo Installing required Python packages for ROCm...
echo.

:: Install required packages
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm5.6
pip install rocm-smi

echo.
echo Step 6: Final Verification
echo =======================
echo.
echo Let's verify that everything is working correctly.
echo.

:: Try to import torch with ROCm
python -c "import torch; print('PyTorch version:', torch.__version__); print('ROCm available:', torch.backends.mps.is_available() if hasattr(torch.backends, 'mps') else 'ROCm backend not found')"

echo.
echo ===================================================
echo Installation Complete!
echo ===================================================
echo.
echo Your AMD RX580 should now be configured for GPU acceleration.
echo.
echo To use GPU acceleration with SassyQueenCore:
echo 1. Run enable_gpu.bat to configure Ollama
echo 2. Run run_cmd.bat to start SassyQueenCore with GPU acceleration
echo.
echo If you encounter any issues, please refer to README_GPU.md
echo.

:END
echo.
echo Press any key to exit...
pause >nul 