#!/usr/bin/env python3
"""
GPU Acceleration Setup for SassyQueenCore's Ollama Integration
Configures Ollama to use the AMD RX590 GPU for accelerated inference
"""

import os
import sys
import json
import requests
import subprocess
import platform
import time
from pathlib import Path

def print_header():
    """Print the script header"""
    print("\n" + "=" * 60)
    print("SassyQueenCore GPU Acceleration Setup".center(60))
    print("For AMD RX590".center(60))
    print("=" * 60 + "\n")

def check_gpu():
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
                if "RX590" in gpu.Name or "RX 590" in gpu.Name:
                    print("✓ AMD RX590 detected!")
                    return True
            
            print("✗ AMD RX590 not found in system.")
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

def check_rocm():
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
            
            print("✗ ROCm not found. GPU acceleration may not work.")
            print("  Please install ROCm from: https://www.amd.com/en/products/software/rocm.html")
            return False
            
        else:
            # Check for ROCm on Linux
            try:
                output = subprocess.check_output(["rocm-smi"], stderr=subprocess.STDOUT).decode("utf-8")
                print("✓ ROCm found and working.")
                return True
            except:
                print("✗ ROCm not found or not working.")
                print("  Please install ROCm from: https://www.amd.com/en/products/software/rocm.html")
                return False
    except Exception as e:
        print(f"Error checking ROCm: {str(e)}")
        return False

def check_ollama():
    """Check Ollama service and GPU configuration"""
    print("\nChecking Ollama service...")
    
    try:
        # Check if Ollama is running
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            print("✓ Ollama service is running.")
            
            # Check if llama3 model is available
            models = response.json().get("models", [])
            llama3_found = False
            
            for model in models:
                if model.get("name") == "llama3:latest":
                    llama3_found = True
                    print("✓ llama3 model is available.")
                    break
            
            if not llama3_found:
                print("✗ llama3 model not found. Please pull it with: ollama pull llama3")
            
            return True
        else:
            print(f"✗ Ollama returned unexpected status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Ollama service is not running.")
        print("  Please start Ollama before continuing.")
        return False
    except Exception as e:
        print(f"Error checking Ollama: {str(e)}")
        return False

def configure_gpu_acceleration():
    """Configure Ollama for GPU acceleration"""
    print("\nConfiguring GPU acceleration for Ollama...")
    
    # Check for Ollama configuration directory
    if platform.system() == "Windows":
        ollama_dir = os.path.expandvars(r"%USERPROFILE%\.ollama")
    else:
        ollama_dir = os.path.expanduser("~/.ollama")
        
    os.makedirs(ollama_dir, exist_ok=True)
    
    # Create or update ollama config
    config_path = os.path.join(ollama_dir, "config.json")
    
    try:
        config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        
        # Set GPU acceleration options
        config["gpu"] = "amd"
        config["gpu_layers"] = -1  # Use all available layers
        config["compute_unit"] = "gpu"  # Force GPU compute
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        print("✓ Ollama configuration updated for GPU acceleration.")
        print(f"  Configuration saved to: {config_path}")
        return True
    except Exception as e:
        print(f"Error configuring GPU acceleration: {str(e)}")
        return False

def restart_ollama():
    """Restart Ollama service to apply configuration"""
    print("\nRestarting Ollama service...")
    
    try:
        if platform.system() == "Windows":
            # On Windows, find and restart the Ollama process
            try:
                # Stop Ollama
                subprocess.run(["taskkill", "/F", "/IM", "ollama.exe"], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
                print("✓ Stopped Ollama service.")
                
                # Wait briefly
                time.sleep(2)
                
                # Start Ollama
                subprocess.Popen(["ollama", "serve"], 
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
                print("✓ Started Ollama service with new configuration.")
                
                # Wait for service to start
                time.sleep(5)
                return True
            except Exception as e:
                print(f"Error restarting Ollama: {str(e)}")
                print("  Please restart Ollama manually to apply changes.")
                return False
        else:
            # On Linux, use systemctl if available
            try:
                subprocess.run(["systemctl", "restart", "ollama"], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
                print("✓ Restarted Ollama service.")
                
                # Wait for service to start
                time.sleep(5)
                return True
            except:
                print("  Please restart Ollama manually to apply changes.")
                return False
    except Exception as e:
        print(f"Error restarting Ollama: {str(e)}")
        return False

def test_gpu_acceleration():
    """Test if GPU acceleration is working"""
    print("\nTesting GPU acceleration...")
    
    try:
        # Simple inference test
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": "Test GPU acceleration. Please respond with a short message.",
                "stream": False,
                "options": {
                    "num_gpu": 99  # Request maximum GPU usage
                }
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✓ Model inference successful!")
            print(f"  Response: {result.get('response', '')[:50]}...")
            
            # Check if there's a way to verify GPU usage
            print("\nNOTE: To verify GPU usage:")
            if platform.system() == "Windows":
                print("  Open AMD Radeon Software and monitor GPU usage")
                print("  or use Task Manager (Performance tab) while generating responses.")
            else:
                print("  Run 'rocm-smi' in another terminal while generating responses.")
            
            return True
        else:
            print(f"✗ Model inference failed: {response.status_code}")
            print(f"  Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error testing GPU acceleration: {str(e)}")
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
    
    # Perform checks
    gpu_available = check_gpu()
    rocm_available = check_rocm()
    ollama_running = check_ollama()
    
    if not gpu_available:
        print("\n⚠ AMD RX590 GPU not detected. Acceleration may not work properly.")
        proceed = input("Do you want to continue anyway? (y/n): ").lower()
        if proceed != 'y':
            print("Aborted.")
            return
    
    if not ollama_running:
        print("\n⚠ Ollama service is not running. Please start it before continuing.")
        proceed = input("Do you want to continue configuration anyway? (y/n): ").lower()
        if proceed != 'y':
            print("Aborted.")
            return
    
    # Configure GPU acceleration
    config_success = configure_gpu_acceleration()
    if not config_success:
        print("\n⚠ Failed to configure GPU acceleration.")
        proceed = input("Do you want to continue anyway? (y/n): ").lower()
        if proceed != 'y':
            print("Aborted.")
            return
    
    # Update SassyQueenCore configuration
    update_sassy_config()
    
    # Restart Ollama
    restart_success = restart_ollama()
    if restart_success:
        # Test GPU acceleration
        test_gpu_acceleration()
    
    print("\n" + "=" * 60)
    print("Setup Complete".center(60))
    print("=" * 60)
    print("\nYour RX590 should now be utilized for faster responses.")
    print("When using SassyQueenCore, you should notice improved response times.")
    print("\nIf you encounter any issues:")
    print("1. Ensure AMD GPU drivers are up-to-date")
    print("2. Check that ROCm is properly installed")
    print("3. Restart Ollama manually if needed")
    print("\nEnjoy your accelerated connection!\n")
    
    input("Press Enter to exit...")

if __name__ == "__main__":
    main() 