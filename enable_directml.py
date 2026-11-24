#!/usr/bin/env python3
"""
DirectML Acceleration Setup for SassyQueenCore
Configures DirectML for AMD RX580 GPU acceleration
"""

import os
import sys
import platform
import subprocess
import json
from pathlib import Path

def print_header():
    """Print the script header"""
    print("\n" + "=" * 60)
    print("SassyQueenCore DirectML Acceleration Setup".center(60))
    print("For AMD RX580".center(60))
    print("=" * 60 + "\n")

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
    except Exception as e:
        print(f"Error checking GPU: {str(e)}")
        return False

def install_directml():
    """Install DirectML and required packages"""
    print("\nInstalling DirectML and required packages...")
    
    try:
        # Uninstall existing torch first to avoid conflicts
        print("  Removing existing PyTorch installation...")
        subprocess.run([
            sys.executable, "-m", "pip", "uninstall", 
            "torch", "torchvision", "torchaudio", "-y"
        ], capture_output=True)
        
        # Install torch-directml (includes compatible PyTorch)
        print("  Installing torch-directml...")
        subprocess.run([
            sys.executable, "-m", "pip", "install",
            "torch-directml"
        ], check=True)
        
        # Install transformers for HuggingFace model support
        print("  Installing transformers...")
        subprocess.run([
            sys.executable, "-m", "pip", "install",
            "transformers", "safetensors", "accelerate"
        ], check=True)
        
        print("✓ DirectML and dependencies installed successfully.")
        return True
    except Exception as e:
        print(f"Error installing packages: {str(e)}")
        return False

def verify_directml():
    """Verify DirectML installation"""
    print("\nVerifying DirectML installation...")
    
    try:
        # Try to import DirectML
        import torch
        import torch_directml
        
        # Create DirectML device
        dml = torch_directml.device()
        
        # Test with a simple tensor
        x = torch.rand(5, 3).to(dml)
        print("✓ Successfully created tensor on DirectML device.")
        
        print(f"✓ DirectML version: {torch_directml.__version__}")
        print(f"✓ PyTorch version: {torch.__version__}")
        return True
    except Exception as e:
        print(f"Error verifying DirectML: {str(e)}")
        return False

def update_ollama_config():
    """Update Ollama configuration for DirectML"""
    print("\nUpdating Ollama configuration...")
    
    try:
        # Get Ollama config directory
        if platform.system() == "Windows":
            ollama_dir = os.path.expandvars(r"%USERPROFILE%\.ollama")
        else:
            ollama_dir = os.path.expanduser("~/.ollama")
            
        os.makedirs(ollama_dir, exist_ok=True)
        
        # Create or update config
        config_path = os.path.join(ollama_dir, "config.json")
        config = {}
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        
        # Update configuration
        config["gpu"] = "directml"
        config["gpu_layers"] = -1  # Use all available layers
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        print("✓ Ollama configuration updated for DirectML.")
        return True
    except Exception as e:
        print(f"Error updating Ollama config: {str(e)}")
        return False

def update_sassy_config():
    """Update SassyQueenCore configuration"""
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
            config["gpu_backend"] = "directml"
            
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
    
    # Check for AMD GPU
    gpu_available = check_amd_gpu()
    if not gpu_available:
        print("\n⚠ AMD RX580 GPU not detected. DirectML may not work properly.")
        proceed = input("Do you want to continue anyway? (y/n): ").lower()
        if proceed != 'y':
            print("Aborted.")
            return
    
    # Install DirectML
    if not install_directml():
        print("Failed to install DirectML.")
        return
    
    # Verify installation
    if not verify_directml():
        print("Failed to verify DirectML installation.")
        return
    
    # Update configurations
    update_ollama_config()
    update_sassy_config()
    
    print("\n" + "=" * 60)
    print("Setup Complete!".center(60))
    print("=" * 60)
    print("\nYour AMD RX580 should now be configured for DirectML acceleration.")
    print("When using SassyQueenCore, you should notice improved response times.")
    print("\nIf you encounter any issues:")
    print("1. Ensure AMD GPU drivers are up-to-date")
    print("2. Restart your computer if needed")
    print("3. Check Windows Event Viewer for any DirectML errors")
    print("\nEnjoy your accelerated connection!\n")
    
    input("Press Enter to exit...")

if __name__ == "__main__":
    main() 