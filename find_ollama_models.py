#!/usr/bin/env python3
"""
Ollama Model Finder Utility
Helps locate Ollama models on your system for use with the GGUF extractor.
"""

import os
import sys
import json
from pathlib import Path
import platform

def find_ollama_models():
    """Find Ollama models on the system"""
    models = []
    
    # Common Ollama model locations by OS
    if platform.system() == "Windows":
        possible_paths = [
            os.path.expanduser("~/.ollama/models"),
            os.path.expanduser("~/AppData/Local/ollama/models"),
            os.path.expanduser("~/AppData/Roaming/ollama/models"),
            "C:/Users/Public/.ollama/models",
            "C:/ProgramData/ollama/models"
        ]
    elif platform.system() == "Darwin":  # macOS
        possible_paths = [
            os.path.expanduser("~/.ollama/models"),
            "/usr/local/share/ollama/models",
            "/opt/homebrew/share/ollama/models"
        ]
    else:  # Linux
        possible_paths = [
            os.path.expanduser("~/.ollama/models"),
            "/usr/share/ollama/models",
            "/var/lib/ollama/models"
        ]
    
    print("🔍 Searching for Ollama models...")
    print(f"Operating System: {platform.system()}")
    print()
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ Found Ollama directory: {path}")
            
            # Look for blobs directory (where model files are stored)
            blobs_path = os.path.join(path, "blobs")
            if os.path.exists(blobs_path):
                print(f"   📁 Blobs directory: {blobs_path}")
                
                # Find SHA256 files (actual model files)
                for item in os.listdir(blobs_path):
                    if item.startswith("sha256-"):
                        file_path = os.path.join(blobs_path, item)
                        file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                        
                        # Try to identify if it's a GGUF file
                        is_gguf = False
                        try:
                            with open(file_path, 'rb') as f:
                                magic = f.read(4)
                                if magic == b'GGUF':
                                    is_gguf = True
                        except:
                            pass
                        
                        models.append({
                            'path': file_path,
                            'name': item,
                            'size_mb': file_size,
                            'is_gguf': is_gguf
                        })
            
            # Look for manifests directory (model metadata)
            manifests_path = os.path.join(path, "manifests")
            if os.path.exists(manifests_path):
                print(f"   📋 Manifests directory: {manifests_path}")
        else:
            print(f"❌ Not found: {path}")
    
    return models

def display_models(models):
    """Display found models in a nice format"""
    if not models:
        print("\n❌ No Ollama models found!")
        print("Make sure Ollama is installed and you have downloaded some models.")
        print("Try running: ollama pull llama2")
        return
    
    print(f"\n🎯 Found {len(models)} model files:")
    print("=" * 80)
    
    gguf_models = [m for m in models if m['is_gguf']]
    other_models = [m for m in models if not m['is_gguf']]
    
    if gguf_models:
        print(f"\n✅ GGUF Models ({len(gguf_models)} found):")
        print("-" * 50)
        for i, model in enumerate(gguf_models, 1):
            print(f"{i:2d}. {model['name']}")
            print(f"    📁 Path: {model['path']}")
            print(f"    📊 Size: {model['size_mb']:.1f} MB")
            print(f"    🔧 Type: GGUF Model ✅")
            print()
    
    if other_models:
        print(f"\n❓ Other Files ({len(other_models)} found):")
        print("-" * 50)
        for i, model in enumerate(other_models, 1):
            print(f"{i:2d}. {model['name']}")
            print(f"    📁 Path: {model['path']}")
            print(f"    📊 Size: {model['size_mb']:.1f} MB")
            print(f"    🔧 Type: Unknown format")
            print()

def get_model_info():
    """Get additional model information from Ollama"""
    try:
        import subprocess
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            print("\n📋 Installed Ollama Models (from 'ollama list'):")
            print("-" * 50)
            print(result.stdout)
        else:
            print("\n❌ Could not run 'ollama list' command")
    except FileNotFoundError:
        print("\n❌ Ollama command not found in PATH")
    except Exception as e:
        print(f"\n❌ Error running ollama list: {e}")

def main():
    """Main function"""
    print("🦙 Ollama Model Finder")
    print("=" * 50)
    print("This utility helps you find Ollama models for use with the GGUF extractor.")
    print()
    
    # Find models
    models = find_ollama_models()
    
    # Display results
    display_models(models)
    
    # Get additional info from Ollama
    get_model_info()
    
    # Instructions
    print("\n💡 How to use with GGUF Extractor:")
    print("-" * 40)
    print("1. Copy the full path of a GGUF model from above")
    print("2. Open the GGUF Model Extractor GUI")
    print("3. Paste the path in the file selection field")
    print("4. Or use 'Browse' and navigate to the path")
    print()
    print("🚀 To launch the GGUF extractor:")
    print("   python gguf_model_extractor.py")
    print("   or double-click: launch_gguf_extractor.bat")

if __name__ == "__main__":
    main() 