#!/usr/bin/env python3
"""Quick diagnostic to check Python version and llama-cpp"""
import sys
import os

print("=" * 50)
print("Python Diagnostic")
print("=" * 50)
print(f"\nPython executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Version info: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

print("\n" + "=" * 50)
print("llama-cpp-python Test")
print("=" * 50)

try:
    from llama_cpp import Llama
    import llama_cpp
    print(f"\n✓ llama-cpp-python version: {llama_cpp.__version__}")
    print(f"✓ Module location: {llama_cpp.__file__}")
    
    # Try to actually create a minimal instance
    print("\nAttempting minimal Llama initialization test...")
    
    # Check if there's a GGUF file to test with
    gguf_files = []
    llm_dir = os.path.join(os.path.dirname(__file__), "llm")
    if os.path.exists(llm_dir):
        for f in os.listdir(llm_dir):
            if f.endswith('.gguf'):
                gguf_files.append(os.path.join(llm_dir, f))
    
    if gguf_files:
        print(f"\nFound GGUF file: {gguf_files[0]}")
        print("Attempting to load with minimal settings...")
        try:
            model = Llama(
                model_path=gguf_files[0],
                n_ctx=128,
                n_batch=32,
                n_threads=1,
                n_gpu_layers=0,
                use_mmap=False,
                use_mlock=False,
                verbose=True  # Show detailed output
            )
            print("\n✓ SUCCESS! Model loaded!")
            del model
        except Exception as e:
            print(f"\n✗ FAILED to load model: {e}")
    else:
        print("\nNo GGUF files found in llm/ folder to test with")
        
except ImportError as e:
    print(f"\n✗ Could not import llama_cpp: {e}")
except Exception as e:
    print(f"\n✗ Error: {e}")

print("\n" + "=" * 50)
input("Press Enter to exit...")
