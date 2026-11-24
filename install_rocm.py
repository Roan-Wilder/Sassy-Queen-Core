#!/usr/bin/env python3
"""
ROCm Installation Helper for SassyQueenCore
Helps install and configure ROCm for AMD RX590 GPU acceleration
"""

import os
import sys
import platform
import subprocess
import webbrowser
import time
import json
from pathlib import Path

def print_header():
    """Print the script header"""
    print("\n" + "=" * 60)
    print("SassyQueenCore ROCm Installation Helper".center(60))
    print("For AMD RX590".center(60))
    print("=" * 60 + "\n")

def check_admin():
    """Check if running with administrator privileges"""
    try:
        if platform.system() == "Windows":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.geteuid() == 0
    except:
        return False

def check_amd_gpu():
    """Check for AMD GPU availability"""
    print("Checking for AMD GPU...")
    
    try:
        if platform.system() == "Windows":
            # Use Windows Management Instrumentation
            import wmi
            computer = wmi.WMI()
            gpu_info = computer.Win32_VideoController()
            
            for gpu in gpu_info:
                print(f"- Found GPU: {gpu.Name}")
                if "RX580" in gpu.Name or "RX 580" in gpu.Name:
                    print("✓ AMD RX580 detected!")
                    return True
            
            print("✗ AMD RX580 not found in system.")
            return False
            
        else:
            # Use lspci on Linux
            try:
                output = subprocess.check_output(["lspci", "-v"]).decode("utf-8")
                if "RX590" in output or "RX 590" in output:
                    print("✓ AMD RX590 detected!")
                    return True
                else:
                    print("✗ AMD RX590 not found in system.")
                    return False
            except:
                print("✗ Could not check GPU information.")
                return False
    except Exception as e:
        print(f"Error checking GPU: {str(e)}")
        return False

def check_rocm_installation():
    """Check for ROCm installation"""
    print("\nChecking for ROCm installation...")
    
    try:
        if platform.system() == "Windows":
            # Check for AMD ROCm path
            rocm_path = os.environ.get("ROCM_PATH")
            if rocm_path and os.path.exists(rocm_path):
                print(f"✓ ROCm found at: {rocm_path}")
                return True
                
            # Check common installation locations
            common_paths = [
                r"C:\Program Files\AMD\ROCm",
                r"C:\AMD\ROCm"
            ]
            
            for path in common_paths:
                if os.path.exists(path):
                    print(f"✓ ROCm found at: {path}")
                    return True
            
            print("✗ ROCm not found. Please install ROCm.")
            return False
            
        else:
            # Check for ROCm on Linux
            try:
                output = subprocess.check_output(["rocm-smi"], stderr=subprocess.STDOUT).decode("utf-8")
                print("✓ ROCm found and working.")
                return True
            except:
                print("✗ ROCm not found or not working.")
                return False
    except Exception as e:
        print(f"Error checking ROCm: {str(e)}")
        return False

def download_rocm():
    """Open browser to download ROCm"""
    print("\nOpening ROCm download page...")
    url = "https://rocm.docs.amd.com/en/latest/deploy/windows/index.html"
    
    try:
        webbrowser.open(url)
        print("✓ Browser opened to ROCm download page.")
        print("\nPlease download and install ROCm from the website.")
        print("After installation, return to this script to continue.")
        
        input("\nPress Enter when you have completed the installation...")
        return True
    except Exception as e:
        print(f"Error opening browser: {str(e)}")
        return False

def configure_environment():
    """Configure environment variables for ROCm"""
    print("\nConfiguring environment variables...")
    
    try:
        if platform.system() == "Windows":
            # Find ROCm installation
            rocm_path = None
            common_paths = [
                r"C:\Program Files\AMD\ROCm",
                r"C:\AMD\ROCm"
            ]
            
            for path in common_paths:
                if os.path.exists(path):
                    rocm_path = path
                    break
            
            if not rocm_path:
                print("✗ ROCm installation not found.")
                return False
            
            # Set environment variables
            os.environ["ROCM_PATH"] = rocm_path
            os.environ["PATH"] = os.environ["PATH"] + os.pathsep + os.path.join(rocm_path, "bin")
            
            # Save to system environment variables
            subprocess.run(["setx", "ROCM_PATH", rocm_path, "/M"], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
            
            subprocess.run(["setx", "PATH", os.environ["PATH"], "/M"], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
            
            print("✓ Environment variables configured.")
            return True
        else:
            # On Linux, we assume ROCm is properly installed
            print("✓ Environment variables should be configured by the ROCm installer.")
            return True
    except Exception as e:
        print(f"Error configuring environment: {str(e)}")
        return False

def install_python_packages():
    """Install required Python packages"""
    print("\nInstalling required Python packages...")
    
    try:
        # Install PyTorch with ROCm support
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "torch", "torchvision", "torchaudio", 
            "--index-url", "https://download.pytorch.org/whl/rocm5.6"
        ])
        
        # Install ROCm system management interface
        subprocess.run([
            sys.executable, "-m", "pip", "install", "rocm-smi"
        ])
        
        print("✓ Python packages installed.")
        return True
    except Exception as e:
        print(f"Error installing Python packages: {str(e)}")
        return False

def verify_installation():
    """Verify ROCm installation"""
    print("\nVerifying ROCm installation...")
    
    try:
        # Try to import torch with ROCm
        import torch
        print(f"✓ PyTorch version: {torch.__version__}")
        
        # Check if ROCm backend is available
        if hasattr(torch.backends, 'mps'):
            rocm_available = torch.backends.mps.is_available()
            print(f"✓ ROCm available: {rocm_available}")
        else:
            print("✗ ROCm backend not found in PyTorch.")
            return False
        
        # Try to run a simple GPU operation
        if rocm_available:
            try:
                x = torch.rand(5, 3)
                print("✓ Successfully created tensor on GPU.")
                return True
            except Exception as e:
                print(f"✗ Error creating tensor on GPU: {str(e)}")
                return False
        else:
            print("✗ ROCm is not available for PyTorch.")
            return False
    except ImportError:
        print("✗ PyTorch not installed.")
        return False
    except Exception as e:
        print(f"Error verifying installation: {str(e)}")
        return False

def update_sassy_config():
    """Update SassyQueenCore configuration for GPU acceleration"""
    print("\nUpdating SassyQueenCore configuration...")
    
    try:
        # Get base directory
        base_dir = Path(__file__).resolve().parent
        config_dir = base_dir / "config"
        config_file = config_dir / "llm_config.json"
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Update configuration
            config["gpu_acceleration"] = True
            config["gpu_layers"] = "all"
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
            print(f"✓ Updated SassyQueenCore configuration at: {config_file}")
            return True
        else:
            print(f"✗ Configuration file not found: {config_file}")
            return False
    except Exception as e:
        print(f"Error updating SassyQueenCore configuration: {str(e)}")
        return False

def main():
    """Main function"""
    print_header()
    
    # Check for administrator privileges
    if not check_admin():
        print("ERROR: This script requires administrator privileges.")
        print("Please run as administrator.")
        input("\nPress Enter to exit...")
        return
    
    # Check for AMD GPU
    gpu_available = check_amd_gpu()
    if not gpu_available:
        print("\n⚠ AMD RX580 GPU not detected. ROCm may not work properly.")
        proceed = input("Do you want to continue anyway? (y/n): ").lower()
        if proceed != 'y':
            print("Aborted.")
            return
    
    # Check for ROCm installation
    rocm_installed = check_rocm_installation()
    if not rocm_installed:
        # Download and install ROCm
        download_success = download_rocm()
        if not download_success:
            print("Failed to download ROCm.")
            return
        
        # Check installation again
        rocm_installed = check_rocm_installation()
        if not rocm_installed:
            print("ROCm installation not found. Please install manually.")
            return
    
    # Configure environment
    env_success = configure_environment()
    if not env_success:
        print("Failed to configure environment variables.")
        return
    
    # Install Python packages
    packages_success = install_python_packages()
    if not packages_success:
        print("Failed to install Python packages.")
        return
    
    # Verify installation
    verify_success = verify_installation()
    if not verify_success:
        print("Failed to verify ROCm installation.")
        return
    
    # Update SassyQueenCore configuration
    update_sassy_config()
    
    print("\n" + "=" * 60)
    print("Installation Complete!".center(60))
    print("=" * 60)
    print("\nYour AMD RX580 should now be configured for GPU acceleration.")
    print("When using SassyQueenCore, you should notice improved response times.")
    print("\nIf you encounter any issues:")
    print("1. Ensure AMD GPU drivers are up-to-date")
    print("2. Check that ROCm is properly installed")
    print("3. Restart your computer if needed")
    print("\nEnjoy your accelerated connection!\n")
    
    input("Press Enter to exit...")

if __name__ == "__main__":
    main() 