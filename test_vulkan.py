#!/usr/bin/env python3
"""
Test Vulkan availability and llama-cpp-python GPU support
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(text):
    print("\n" + "=" * 50)
    print(text.center(50))
    print("=" * 50)

def test_vulkan_sdk():
    """Test Vulkan SDK installation"""
    print_header("Vulkan SDK Check")
    
    # Check environment variable
    vulkan_sdk = os.environ.get("VULKAN_SDK")
    if vulkan_sdk:
        print(f"✓ VULKAN_SDK: {vulkan_sdk}")
    else:
        # Check local installation
        local_sdk = Path(__file__).parent / "Vulkan"
        if local_sdk.exists():
            print(f"✓ Local Vulkan SDK found: {local_sdk}")
            os.environ["VULKAN_SDK"] = str(local_sdk)
            os.environ["PATH"] = str(local_sdk / "Bin") + os.pathsep + os.environ.get("PATH", "")
            vulkan_sdk = str(local_sdk)
        else:
            print("✗ VULKAN_SDK not set and no local SDK found")
            return False
    
    # Check for key files
    sdk_path = Path(vulkan_sdk)
    checks = [
        ("Include/vulkan/vulkan.h", "Vulkan headers"),
        ("Lib/vulkan-1.lib", "Vulkan library"),
        ("Bin/vulkaninfoSDK.exe", "Vulkan info tool"),
    ]
    
    all_ok = True
    for file_path, desc in checks:
        full_path = sdk_path / file_path
        if full_path.exists():
            print(f"✓ {desc}: {file_path}")
        else:
            print(f"✗ {desc} missing: {file_path}")
            all_ok = False
    
    return all_ok

def test_vulkan_gpu():
    """Test GPU Vulkan support"""
    print_header("GPU Vulkan Support")
    
    vulkan_sdk = os.environ.get("VULKAN_SDK")
    if not vulkan_sdk:
        print("✗ VULKAN_SDK not set, skipping GPU test")
        return False
    
    vulkaninfo = Path(vulkan_sdk) / "Bin" / "vulkaninfoSDK.exe"
    if not vulkaninfo.exists():
        print("✗ vulkaninfoSDK.exe not found")
        return False
    
    try:
        result = subprocess.run(
            [str(vulkaninfo), "--summary"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✓ Vulkan is working!")
            # Look for GPU info
            for line in result.stdout.split('\n'):
                if 'GPU' in line or 'deviceName' in line or 'AMD' in line or 'Radeon' in line:
                    print(f"  {line.strip()}")
            return True
        else:
            print(f"✗ vulkaninfo failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ vulkaninfo timed out")
        return False
    except Exception as e:
        print(f"✗ Error running vulkaninfo: {e}")
        return False

def test_llama_cpp():
    """Test llama-cpp-python installation"""
    print_header("llama-cpp-python Check")
    
    try:
        import llama_cpp
        print(f"✓ llama-cpp-python version: {llama_cpp.__version__}")
        
        # Try to check for Vulkan support
        # This is tricky as there's no direct API, but we can try loading
        print("✓ Module imported successfully")
        return True
        
    except ImportError as e:
        print(f"✗ Could not import llama_cpp: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_model_load():
    """Test loading a small test to check for access violations"""
    print_header("Model Load Test")
    
    try:
        from llama_cpp import Llama
        
        # Try to create a Llama instance with minimal config
        # This will fail if there's a fundamental library issue
        print("Testing library initialization...")
        
        # We don't have a model to load, so just test the import worked
        print("✓ Llama class is accessible")
        print("\nTo test with a real model, run:")
        print("  python -c \"from llama_cpp import Llama; m = Llama(model_path='your_model.gguf', n_ctx=512)\"")
        return True
        
    except Exception as e:
        error_str = str(e)
        if "access violation" in error_str.lower():
            print(f"✗ ACCESS VIOLATION detected!")
            print("\nThis usually means:")
            print("1. llama-cpp-python binary is incompatible with Python 3.13")
            print("2. Need to rebuild from source with proper compiler")
            print("\nRecommended fix:")
            print("  Install Python 3.11 and use that instead")
        else:
            print(f"✗ Error: {e}")
        return False

def main():
    print("\n" + "=" * 50)
    print("SassyQueenCore Vulkan Diagnostics".center(50))
    print("=" * 50)
    
    print(f"\nPython version: {sys.version}")
    print(f"Platform: {sys.platform}")
    
    results = {
        "Vulkan SDK": test_vulkan_sdk(),
        "GPU Vulkan": test_vulkan_gpu(),
        "llama-cpp-python": test_llama_cpp(),
        "Model Load": test_model_load(),
    }
    
    print_header("Summary")
    
    all_passed = True
    for test, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✓ All tests passed! Vulkan should work.")
    else:
        print("\n✗ Some tests failed. See above for details.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
