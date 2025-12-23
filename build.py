import os
import sys
import subprocess
import shutil
import platform

def clean_build():
    """Removes build and dist directories."""
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            print(f"Cleaning {folder}...")
            shutil.rmtree(folder)

def build():
    """Runs PyInstaller based on the current OS."""
    os_name = platform.system()
    print(f"Detected OS: {os_name}")
    
    # Ensure static directory exists
    if not os.path.exists("static"):
        os.makedirs("static")
    
    # PyInstaller command
    # We assume 'pyinstaller' is in the PATH. If not, we might need to call it via 'python -m PyInstaller'
    cmd = [sys.executable, "-m", "PyInstaller", "BehaveRunner.spec", "--noconfirm", "--clean"]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("Build successful!")
        print(f"Executable can be found in: dist/BehaveRunner")
    else:
        print("Build failed.")
        sys.exit(result.returncode)

if __name__ == "__main__":
    clean_build()
    build()
