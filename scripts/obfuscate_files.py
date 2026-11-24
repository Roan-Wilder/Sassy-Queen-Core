import os
import subprocess

# 📍 Adjust to your actual app script directory
SOURCE_DIR = "C:\Pro\scripts"
OUTPUT_DIR = "C:\Pro\build"

# 🧹 Clean build dir
if os.path.exists(OUTPUT_DIR):
    import shutil
    shutil.rmtree(OUTPUT_DIR)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ⚔️ Files you want to obfuscate (only .py files, not full folders)
for filename in os.listdir(SOURCE_DIR):
    if filename.endswith(".py") and filename != "setup.py":
        source_file = os.path.join(SOURCE_DIR, filename)
        print(f"⚙️ Obfuscating: {filename}")

        # 🔐 Obfuscation using Nuitka
        subprocess.run([
            "python",
            "-m", "nuitka",
            "--remove-output",
            "--follow-imports",
            "--nofollow-import-to=*.tests",
            "--nofollow-import-to=*.devtools",
            "--output-dir=" + OUTPUT_DIR,
            "--python-flag=no_site",
            "--module",  # Compile to .pyd so it acts like a regular Python import
            "--lto=no",  # Can be enabled if you want more optimization
            source_file
        ])
