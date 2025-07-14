#!/usr/bin/env python3
"""
Cross-platform setup script for MeshPy UI
Automatically handles virtual environment creation and dependency installation
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def get_platform():
    """Detect the current platform"""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    else:
        return "unknown"

def run_command(cmd, shell=False):
    """Run a command and handle errors"""
    try:
        print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        if shell:
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        else:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False

def check_python():
    """Check if Python 3.8+ is available"""
    try:
        version = sys.version_info
        if version.major >= 3 and version.minor >= 8:
            print(f"✓ Python {version.major}.{version.minor}.{version.micro} found")
            return True
        else:
            print(f"✗ Python {version.major}.{version.minor}.{version.micro} found, but 3.8+ required")
            return False
    except:
        print("✗ Python not found")
        return False

def create_venv(platform_type):
    """Create virtual environment based on platform"""
    venv_name = "venv"
    
    # Remove existing venv if it exists
    if os.path.exists(venv_name):
        print(f"Removing existing {venv_name} directory...")
        shutil.rmtree(venv_name)
    
    # Create new virtual environment
    print("Creating virtual environment...")
    if platform_type == "windows":
        return run_command([sys.executable, "-m", "venv", venv_name])
    else:
        return run_command([sys.executable, "-m", "venv", venv_name])

def get_activation_command(platform_type):
    """Get the virtual environment activation command"""
    if platform_type == "windows":
        return "venv\\Scripts\\activate"
    else:
        return "source venv/bin/activate"

def get_python_executable(platform_type):
    """Get the Python executable path in the virtual environment"""
    if platform_type == "windows":
        return "venv\\Scripts\\python.exe"
    else:
        return "venv/bin/python"

def install_dependencies(platform_type):
    """Install dependencies in the virtual environment"""
    python_exe = get_python_executable(platform_type)
    
    print("Upgrading pip...")
    if not run_command([python_exe, "-m", "pip", "install", "--upgrade", "pip"]):
        return False
    
    print("Installing dependencies...")
    if not run_command([python_exe, "-m", "pip", "install", "-r", "requirements.txt"]):
        return False
    
    return True

def create_run_script(platform_type):
    """Create a simple run script"""
    if platform_type == "windows":
        script_name = "run.bat"
        script_content = f"""@echo off
echo Starting MeshPy UI...
call venv\\Scripts\\activate
python main.py
pause
"""
    else:
        script_name = "run.sh"
        script_content = f"""#!/bin/bash
echo "Starting MeshPy UI..."
source venv/bin/activate
python main.py
"""
    
    with open(script_name, "w") as f:
        f.write(script_content)
    
    if platform_type != "windows":
        os.chmod(script_name, 0o755)
    
    print(f"✓ Created {script_name} for easy running")

def main():
    """Main setup function"""
    print("=" * 60)
    print("MeshPy UI - Cross-Platform Setup")
    print("=" * 60)
    
    # Detect platform
    platform_type = get_platform()
    print(f"Platform detected: {platform_type}")
    
    if platform_type == "unknown":
        print("❌ Unsupported platform")
        sys.exit(1)
    
    # Check Python version
    if not check_python():
        print("❌ Please install Python 3.8 or higher")
        sys.exit(1)
    
    # Create virtual environment
    print("\n" + "=" * 40)
    print("Creating Virtual Environment")
    print("=" * 40)
    
    if not create_venv(platform_type):
        print("❌ Failed to create virtual environment")
        sys.exit(1)
    
    print("✓ Virtual environment created successfully")
    
    # Install dependencies
    print("\n" + "=" * 40)
    print("Installing Dependencies")
    print("=" * 40)
    
    if not install_dependencies(platform_type):
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    print("✓ Dependencies installed successfully")
    
    # Create run script
    print("\n" + "=" * 40)
    print("Creating Run Script")
    print("=" * 40)
    
    create_run_script(platform_type)
    
    # Create database directory
    os.makedirs("database", exist_ok=True)
    
    # Final instructions
    print("\n" + "=" * 60)
    print("Setup Complete! 🎉")
    print("=" * 60)
    print("To run MeshPy UI:")
    print()
    
    if platform_type == "windows":
        print("  Double-click: run.bat")
        print("  Or from command line: run.bat")
    else:
        print("  From terminal: ./run.sh")
    
    print("\nAlternatively, you can run manually:")
    activation_cmd = get_activation_command(platform_type)
    print(f"  {activation_cmd}")
    print("  python main.py")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main() 