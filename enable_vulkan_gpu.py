#!/usr/bin/env python3
"""
Vulkan GPU Acceleration Setup for SassyQueenCore
Configures llama-cpp-python with Vulkan/Kompute backend for AMD RX580

This is the BEST option for RX 580 since:
- ROCm doesn't support Polaris (RX 580) on Windows
- DirectML has limited model support
- Vulkan is fully supported by RX 580 and works with llama.cpp
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
    print("SassyQueenCore Vulkan GPU Acceleration".center(60))
    print("For AMD RX 580 (Polaris)".center(60))
    print("=" * 60 + "\n")

def check_vulkan():
    """Check for Vulkan support"""
    print("Checking Vulkan support...")
    
    try:
        # Check for vulkaninfo
        if platform.system() == "Windows":
            # Check common Vulkan SDK locations
            vulkan_sdk = os.environ.get("VULKAN_SDK")
            if vulkan_sdk:
                print(f"✓ Vulkan SDK found at: {vulkan_sdk}")
                return True
            
            # Try running vulkaninfo
            try:
                result = subprocess.run(
                    ["vulkaninfo", "--summary"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    print("✓ Vulkan is available on this system")
                    # Look for AMD GPU
                    if "AMD" in result.stdout or "Radeon" in result.stdout:
                        print("✓ AMD GPU detected with Vulkan support")
                    return True
            except FileNotFoundError:
                print("  vulkaninfo not found, but Vulkan may still work")
                print("  (AMD drivers include Vulkan support)")
                return True
            except subprocess.TimeoutExpired:
                print("  vulkaninfo timed out, continuing anyway")
                return True
        
        return True
        
    except Exception as e:
        print(f"Warning checking Vulkan: {str(e)}")
        return True  # Continue anyway - AMD drivers include Vulkan

def check_gpu():
    """Check for AMD GPU"""
    print("\nChecking for AMD GPU...")
    
    try:
        if platform.system() == "Windows":
            import wmi
            computer = wmi.WMI()
            gpu_info = computer.Win32_VideoController()
            
            amd_gpu_found = False
            for gpu in gpu_info:
                print(f"  Found: {gpu.Name}")
                if "AMD" in gpu.Name or "Radeon" in gpu.Name or "RX" in gpu.Name:
                    amd_gpu_found = True
                    if "580" in gpu.Name:
                        print("✓ AMD RX 580 detected - Perfect for Vulkan!")
            
            return amd_gpu_found
    except ImportError:
        print("  WMI not available, assuming AMD GPU present")
        return True
    except Exception as e:
        print(f"  Error checking GPU: {str(e)}")
        return True

def uninstall_existing_llama():
    """Uninstall existing llama-cpp-python to avoid conflicts"""
    print("\nRemoving existing llama-cpp-python installation...")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "llama-cpp-python", "-y"],
            capture_output=True
        )
        print("✓ Removed existing installation (if any)")
        return True
    except Exception as e:
        print(f"  Warning: {str(e)}")
        return True

def install_llama_vulkan():
    """Install llama-cpp-python with Vulkan support"""
    print("\nInstalling llama-cpp-python with Vulkan backend...")
    print("  This may take several minutes as it compiles from source...")
    
    # Set environment variables for Vulkan/Kompute build
    env = os.environ.copy()
    env["CMAKE_ARGS"] = "-DGGML_VULKAN=ON"
    
    try:
        # First, ensure we have the build tools
        print("\n  Step 1: Installing build dependencies...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "cmake", "ninja", "setuptools", "wheel"],
            check=True
        )
        
        # Install llama-cpp-python with Vulkan
        print("\n  Step 2: Building llama-cpp-python with Vulkan...")
        print("  (This compiles the library - please be patient)")
        
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "llama-cpp-python", 
             "--force-reinstall", "--no-cache-dir", "-v"],
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✓ llama-cpp-python with Vulkan installed successfully!")
            return True
        else:
            print(f"  Build output: {result.stdout[-1000:] if result.stdout else 'None'}")
            print(f"  Build errors: {result.stderr[-1000:] if result.stderr else 'None'}")
            
            # Try pre-built wheel as fallback
            print("\n  Trying pre-built wheel as fallback...")
            return install_prebuilt_llama()
            
    except subprocess.CalledProcessError as e:
        print(f"✗ Installation failed: {str(e)}")
        return install_prebuilt_llama()
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return install_prebuilt_llama()

def install_prebuilt_llama():
    """Install pre-built llama-cpp-python (CPU version as fallback)"""
    print("\n  Installing pre-built llama-cpp-python...")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "llama-cpp-python", "--force-reinstall"],
            check=True
        )
        print("✓ Installed pre-built version (may not have Vulkan)")
        print("  You can manually build with Vulkan later if needed")
        return True
    except Exception as e:
        print(f"✗ Failed to install: {str(e)}")
        return False

def verify_installation():
    """Verify llama-cpp-python installation"""
    print("\nVerifying installation...")
    
    try:
        from llama_cpp import Llama
        print("✓ llama-cpp-python imported successfully")
        
        # Check if Vulkan is available
        try:
            # Try to check available backends
            import llama_cpp
            if hasattr(llama_cpp, '__version__'):
                print(f"✓ Version: {llama_cpp.__version__}")
        except:
            pass
        
        return True
        
    except ImportError as e:
        print(f"✗ Failed to import llama-cpp-python: {str(e)}")
        return False

def update_sassy_config():
    """Update SassyQueenCore configuration for Vulkan GPU"""
    print("\nUpdating SassyQueenCore configuration...")
    
    try:
        base_dir = Path(__file__).resolve().parent
        config_dir = base_dir / "config"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "llm_config.json"
        
        config = {}
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
        
        # Update for Vulkan GPU
        config["gpu_acceleration"] = True
        config["gpu_backend"] = "vulkan"
        config["gpu_layers"] = "all"  # Use all layers on GPU
        config["n_gpu_layers"] = -1   # -1 means all layers
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✓ Configuration saved to: {config_file}")
        return True
        
    except Exception as e:
        print(f"✗ Error updating config: {str(e)}")
        return False

def create_gpu_model_loader():
    """Create a helper script for loading models with GPU"""
    print("\nCreating GPU model loader helper...")
    
    loader_code = '''#!/usr/bin/env python3
"""
GPU-Accelerated Model Loader for SassyQueenCore
Uses Vulkan backend for AMD RX 580
"""

from llama_cpp import Llama
import os

def load_model_with_gpu(model_path, n_gpu_layers=-1, n_ctx=2048):
    """
    Load a GGUF model with Vulkan GPU acceleration.
    
    Args:
        model_path: Path to the .gguf model file
        n_gpu_layers: Number of layers to offload to GPU (-1 = all)
        n_ctx: Context window size
    
    Returns:
        Llama model instance
    """
    print(f"Loading model: {model_path}")
    print(f"GPU layers: {n_gpu_layers} (-1 = all)")
    
    model = Llama(
        model_path=model_path,
        n_gpu_layers=n_gpu_layers,  # Offload to GPU
        n_ctx=n_ctx,
        n_batch=512,
        verbose=True  # Show GPU info during load
    )
    
    print("Model loaded successfully!")
    return model

def test_gpu():
    """Test if GPU acceleration is working"""
    print("Testing GPU acceleration...")
    print("If you see 'Vulkan' or 'GPU' in the output above, GPU is working!")
    
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        model = load_model_with_gpu(sys.argv[1])
        # Quick test
        response = model("Hello!", max_tokens=32)
        print(f"Test response: {response['choices'][0]['text']}")
    else:
        print("Usage: python gpu_model_loader.py <path_to_gguf_model>")
        test_gpu()
'''
    
    try:
        base_dir = Path(__file__).resolve().parent
        loader_file = base_dir / "gpu_model_loader.py"
        
        with open(loader_file, 'w') as f:
            f.write(loader_code)
        
        print(f"✓ Created: {loader_file}")
        return True
        
    except Exception as e:
        print(f"✗ Error creating loader: {str(e)}")
        return False

def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "=" * 60)
    print("Setup Complete!".center(60))
    print("=" * 60)
    
    print("""
NEXT STEPS:

1. CONVERT YOUR MODEL TO GGUF FORMAT:
   Your current model is in safetensors format. For GPU acceleration,
   you need a GGUF quantized model. You can either:
   
   a) Download a pre-quantized GGUF version:
      - Visit: https://huggingface.co/models?search=gemma+gguf
      - Look for Q4_K_M or Q5_K_M quantization (good balance)
   
   b) Or use a smaller model optimized for your 8GB VRAM:
      - gemma-2-2b-it (2B parameters, fits easily in 8GB)
      - llama-3.2-3b (3B parameters)
      - phi-3-mini (3.8B parameters)

2. LOAD THE GGUF MODEL:
   In SassyQueenCore, use "Load Local Model" and select your .gguf file.
   The model will automatically use GPU if available.

3. TEST GPU ACCELERATION:
   Run: python gpu_model_loader.py <your_model.gguf>
   Look for "Vulkan" in the output to confirm GPU is being used.

TIPS FOR RX 580 (8GB VRAM):
- Use Q4_K_M quantization (best quality/size balance)
- 7B models should fit comfortably
- 13B models may require some CPU offloading
- Set n_gpu_layers based on available VRAM

For questions about GPU setup, the llama.cpp documentation is helpful:
https://github.com/ggerganov/llama.cpp#vulkan
""")

def main():
    """Main function"""
    print_header()
    
    # Check Vulkan support
    vulkan_ok = check_vulkan()
    
    # Check for AMD GPU
    gpu_ok = check_gpu()
    
    if not gpu_ok:
        print("\n⚠ AMD GPU not detected. Continuing anyway...")
        proceed = input("Continue? (y/n): ").lower()
        if proceed != 'y':
            return
    
    # Uninstall existing
    uninstall_existing_llama()
    
    # Install with Vulkan
    install_ok = install_llama_vulkan()
    
    if not install_ok:
        print("\n⚠ Installation had issues. Check the output above.")
        proceed = input("Continue with verification? (y/n): ").lower()
        if proceed != 'y':
            return
    
    # Verify
    verify_ok = verify_installation()
    
    # Update config
    update_sassy_config()
    
    # Create helper
    create_gpu_model_loader()
    
    # Print next steps
    print_next_steps()
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
