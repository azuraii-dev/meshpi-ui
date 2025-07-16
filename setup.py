#!/usr/bin/env python3
"""
Meshtastic UI Setup Script
Automatically detects OS and sets up the development environment
Now includes executable building functionality
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def detect_platform():
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

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        return False
    return True

def run_command(command, check=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(command, shell=True, check=check, 
                              capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def create_virtual_environment():
    """Create a virtual environment"""
    print("Creating virtual environment...")
    
    if os.path.exists("venv"):
        print("Virtual environment already exists")
        return True
    
    success, stdout, stderr = run_command(f"{sys.executable} -m venv venv")
    if success:
        print("✓ Virtual environment created successfully")
        return True
    else:
        print(f"Failed to create virtual environment: {stderr}")
        return False

def get_pip_command():
    """Get the correct pip command for the current platform"""
    platform_name = detect_platform()
    
    if platform_name == "windows":
        return "venv\\Scripts\\pip"
    else:
        return "venv/bin/pip"

def get_python_command():
    """Get the correct python command for the current platform"""
    platform_name = detect_platform()
    
    if platform_name == "windows":
        return "venv\\Scripts\\python"
    else:
        return "venv/bin/python"

def install_dependencies():
    """Install project dependencies"""
    print("Installing dependencies...")
    
    pip_cmd = get_pip_command()
    
    # Install basic requirements
    success, stdout, stderr = run_command(f"{pip_cmd} install -r requirements.txt")
    if not success:
        print(f"Failed to install dependencies: {stderr}")
        return False
    
    print("✓ Dependencies installed successfully")
    return True

def install_pyinstaller():
    """Install PyInstaller for building executables"""
    print("Installing PyInstaller...")
    
    pip_cmd = get_pip_command()
    success, stdout, stderr = run_command(f"{pip_cmd} install pyinstaller")
    
    if success:
        print("✓ PyInstaller installed successfully")
        return True
    else:
        print(f"Failed to install PyInstaller: {stderr}")
        return False

def build_executable():
    """Build executable using PyInstaller"""
    print("\n" + "="*50)
    print("BUILDING EXECUTABLE")
    print("="*50)
    
    # Check for --all flag
    build_all = "--all" in sys.argv
    if build_all:
        return build_all_platforms()
    
    # Check if virtual environment exists
    if not os.path.exists("venv"):
        print("Virtual environment not found. Creating one...")
        if not create_virtual_environment():
            return False
        if not install_dependencies():
            return False
    
    # Install PyInstaller if not present
    pip_cmd = get_pip_command()
    success, stdout, stderr = run_command(f"{pip_cmd} show pyinstaller", check=False)
    if not success:
        if not install_pyinstaller():
            return False
    
    # Check if spec file exists
    if not os.path.exists("meshpi-ui.spec"):
        print("Spec file not found. Please ensure meshpi-ui.spec exists.")
        return False
    
    # Clean previous builds
    if os.path.exists("dist"):
        print("Cleaning previous build...")
        try:
            shutil.rmtree("dist")
        except PermissionError as e:
            print(f"⚠️  Warning: Could not remove dist directory: {e}")
            print("This usually means MeshtasticUI.exe is still running.")
            print("Please:")
            print("  1. Close any running MeshtasticUI.exe processes")
            print("  2. Wait a moment for file locks to release")
            print("  3. Try the build again")
            print("\nAlternatively, manually delete the 'dist' folder and retry.")
            return False
        except Exception as e:
            print(f"⚠️  Warning: Error removing dist directory: {e}")
            print("Continuing with build...")
    
    if os.path.exists("build"):
        try:
            shutil.rmtree("build")
        except Exception as e:
            print(f"⚠️  Warning: Could not remove build directory: {e}")
            print("Continuing with build...")
    
    # Get platform info
    platform_name = detect_platform()
    python_cmd = get_python_command()
    
    print(f"Building for platform: {platform_name}")
    print("This may take several minutes...")
    
    # Run PyInstaller
    pyinstaller_cmd = f"{python_cmd} -m PyInstaller meshpi-ui.spec"
    print(f"Running: {pyinstaller_cmd}")
    
    success, stdout, stderr = run_command(pyinstaller_cmd)
    
    if success:
        print("\n✓ Executable built successfully!")
        
        # Show output location
        if platform_name == "windows":
            exe_path = "dist/MeshtasticUI.exe"
        elif platform_name == "macos":
            exe_path = "dist/MeshtasticUI.app"
        else:
            exe_path = "dist/MeshtasticUI"
        
        if os.path.exists(exe_path):
            print(f"✓ Executable location: {os.path.abspath(exe_path)}")
            
            # Get file size
            if platform_name == "macos":
                # For .app bundles, get directory size
                total_size = sum(os.path.getsize(os.path.join(dirpath, filename))
                               for dirpath, dirnames, filenames in os.walk(exe_path)
                               for filename in filenames)
            else:
                total_size = os.path.getsize(exe_path)
            
            size_mb = total_size / (1024 * 1024)
            print(f"✓ Executable size: {size_mb:.1f} MB")
        
        return True
    else:
        print(f"\nBuild failed: {stderr}")
        if "No module named" in stderr:
            print("\nTip: Try installing missing dependencies manually:")
            print(f"  {pip_cmd} install <missing_module>")
        return False

def create_platform_spec_files():
    """Create platform-specific spec files"""
    print("Creating platform-specific spec files...")
    
    # Base spec content (without platform-specific parts)
    base_spec_template = '''# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Platform: {platform}
block_cipher = None

# Collect all meshtastic related modules and data
meshtastic_datas, meshtastic_binaries, meshtastic_hiddenimports = collect_all('meshtastic')

# Additional hidden imports for optional dependencies
hiddenimports = [
    'meshtastic',
    'meshtastic.serial_interface',
    'meshtastic.tcp_interface', 
    'meshtastic.ble_interface',
    'meshtastic.mesh_pb2',
    'meshtastic.portnums_pb2',
    'meshtastic.telemetry_pb2',
    'google.protobuf',
    'google.protobuf.message',
    'google.protobuf.descriptor',
    'google.protobuf.internal',
    'serial',
    'serial.tools',
    'serial.tools.list_ports',
    'sqlite3',
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'requests',
    'json',
    'threading',
    'queue',
    'datetime',
    'logging',
    'time',
    'math',
    'os',
    'sys',
    'platform',
    'subprocess',
    'webbrowser',
] + meshtastic_hiddenimports

# Optional dependencies (graceful degradation)
optional_imports = [
    'matplotlib',
    'matplotlib.pyplot',
    'matplotlib.figure',
    'matplotlib.backends.backend_tkagg',
    'matplotlib.dates',
    'matplotlib.ticker',
    'numpy',
    'tkintermapview',
]

# Add optional imports if available
for imp in optional_imports:
    try:
        __import__(imp)
        hiddenimports.append(imp)
    except ImportError:
        pass

# Data files to include
datas = [
    # Include any data files your app needs
] + meshtastic_datas

# Binary files (mainly from meshtastic)
binaries = meshtastic_binaries

# Modules to exclude (reduce file size)
excludes = [
    'IPython',
    'jupyter',
    'notebook',
    'pandas',
    'scipy',
    'sklearn',
    'tensorflow',
    'torch',
    'cv2',
    'babel',
    'docutils',
    'jinja2',
    'markupsafe',
    'pygments',
    'sphinx',
    'tornado',
    'zmq',
    'test',
    'tests',
    'testing',
    'unittest',
    'pydoc',
    'xml.etree.ElementTree',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

{exe_section}

{bundle_section}
'''

    # Platform-specific configurations
    platforms = {
        'windows': {
            'exe_name': 'MeshtasticUI.exe',
            'console': False,
            'icon': 'assets/icon.ico',
            'bundle_section': ''
        },
        'macos': {
            'exe_name': 'MeshtasticUI',
            'console': False,
            'icon': 'assets/icon.icns',
            'bundle_section': '''
# macOS specific: Create .app bundle
app = BUNDLE(
    exe,
    name='MeshtasticUI.app',
    icon=icon if os.path.exists(icon or '') else None,
    bundle_identifier='com.meshpi.ui',
    info_plist={{
        'CFBundleName': 'Meshtastic UI',
        'CFBundleDisplayName': 'Meshtastic UI',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'NSHumanReadableCopyright': 'Copyright © 2024',
        'LSMinimumSystemVersion': '10.9.0',
        'NSRequiresAquaSystemAppearance': False,  # Support dark mode
    }},
)'''
        },
        'linux': {
            'exe_name': 'MeshtasticUI',
            'console': False,
            'icon': 'assets/icon.png',
            'bundle_section': ''
        }
    }
    
    for platform_name, config in platforms.items():
        exe_section = f'''
# Check if icon exists, otherwise don't use it
icon = '{config['icon']}'
if not os.path.exists(icon):
    icon = None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{config['exe_name']}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress executable
    upx_exclude=[],
    runtime_tmpdir=None,
    console={config['console']},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)'''

        spec_content = base_spec_template.format(
            platform=platform_name,
            exe_section=exe_section,
            bundle_section=config['bundle_section']
        )
        
        spec_filename = f"meshpi-ui-{platform_name}.spec"
        with open(spec_filename, 'w') as f:
            f.write(spec_content)
        
        print(f"✓ Created {spec_filename}")
    
    return True

def create_docker_files():
    """Create Docker files for cross-platform building"""
    print("Creating Docker configuration for cross-platform builds...")
    
    # Dockerfile for Linux builds
    dockerfile_linux = '''# Dockerfile for building Meshtastic UI on Linux
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    pkg-config \\
    libbluetooth-dev \\
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir pyinstaller

# Copy source code
COPY . .

# Build the executable
RUN python -m PyInstaller meshpi-ui-linux.spec

# Create output directory
RUN mkdir -p /output
RUN cp -r dist/* /output/

# Volume for output
VOLUME ["/output"]

CMD ["cp", "-r", "dist/*", "/output/"]
'''
    
    with open("Dockerfile.linux", "w") as f:
        f.write(dockerfile_linux)
    print("✓ Created Dockerfile.linux")
    
    # Docker Compose for easy building
    docker_compose = '''version: '3.8'

services:
  build-linux:
    build:
      context: .
      dockerfile: Dockerfile.linux
    volumes:
      - ./dist-linux:/output
    command: sh -c "cp -r dist/* /output/"

  build-windows:
    # Note: Windows builds require Windows containers or cross-compilation tools
    # For now, use GitHub Actions or build on Windows directly
    image: busybox
    command: echo "Windows builds require Windows environment or GitHub Actions"

  build-macos:
    # Note: macOS builds require macOS environment
    # For now, use GitHub Actions or build on macOS directly  
    image: busybox
    command: echo "macOS builds require macOS environment or GitHub Actions"
'''
    
    with open("docker-compose.build.yml", "w") as f:
        f.write(docker_compose)
    print("✓ Created docker-compose.build.yml")
    
    return True

def create_github_actions():
    """Create GitHub Actions workflow for multi-platform builds"""
    print("Creating GitHub Actions workflow for automated multi-platform builds...")
    
    # Create .github/workflows directory
    os.makedirs(".github/workflows", exist_ok=True)
    
    workflow = '''name: Build Multi-Platform Executables

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

jobs:
  build:
    strategy:
      matrix:
        include:
          - os: windows-latest
            platform: windows
            spec: meshpi-ui-windows.spec
            artifact: MeshtasticUI.exe
            
          - os: ubuntu-latest
            platform: linux
            spec: meshpi-ui-linux.spec
            artifact: MeshtasticUI
            
          - os: macos-latest
            platform: macos
            spec: meshpi-ui-macos.spec
            artifact: MeshtasticUI.app

    runs-on: ${{ matrix.os }}
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pyinstaller
    
    - name: Build executable
      run: |
        python -m PyInstaller ${{ matrix.spec }}
    
    - name: Upload artifact
      uses: actions/upload-artifact@v3
      with:
        name: MeshtasticUI-${{ matrix.platform }}
        path: dist/${{ matrix.artifact }}
        
  release:
    if: startsWith(github.ref, 'refs/tags/')
    needs: build
    runs-on: ubuntu-latest
    
    steps:
    - name: Download all artifacts
      uses: actions/download-artifact@v3
    
    - name: Create Release
      uses: softprops/action-gh-release@v1
      with:
        files: |
          MeshtasticUI-windows/*
          MeshtasticUI-linux/*
          MeshtasticUI-macos/*
        draft: false
        prerelease: false
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
'''
    
    with open(".github/workflows/build.yml", "w") as f:
        f.write(workflow)
    print("✓ Created .github/workflows/build.yml")
    
    return True

def build_all_platforms():
    """Prepare build configurations for all platforms"""
    print("\n" + "="*60)
    print("BUILDING FOR ALL PLATFORMS")
    print("="*60)
    
    current_platform = detect_platform()
    print(f"Current platform: {current_platform}")
    print("Note: PyInstaller can only build for the current platform natively.")
    print("Creating configurations for cross-platform building...\n")
    
    # Create platform-specific spec files
    if not create_platform_spec_files():
        return False
    
    # Create Docker files for Linux cross-compilation
    if not create_docker_files():
        return False
    
    # Create GitHub Actions workflow
    if not create_github_actions():
        return False
    
    # Build for current platform
    print(f"\nBuilding for current platform ({current_platform})...")
    spec_file = f"meshpi-ui-{current_platform}.spec"
    
    if os.path.exists(spec_file):
        # Temporarily rename the current spec file
        if os.path.exists("meshpi-ui.spec"):
            shutil.move("meshpi-ui.spec", "meshpi-ui-original.spec")
        shutil.copy(spec_file, "meshpi-ui.spec")
        
        # Build for current platform
        success = build_executable()
        
        # Restore original spec file
        if os.path.exists("meshpi-ui-original.spec"):
            shutil.move("meshpi-ui-original.spec", "meshpi-ui.spec")
        else:
            os.remove("meshpi-ui.spec")
        
        if not success:
            return False
    
    print("\n" + "="*60)
    print("MULTI-PLATFORM BUILD SETUP COMPLETE")
    print("="*60)
    print("✓ Platform-specific spec files created")
    print("✓ Docker configuration created")
    print("✓ GitHub Actions workflow created")
    print(f"✓ Executable built for {current_platform}")
    
    print("\nFILES CREATED:")
    print("- meshpi-ui-windows.spec")
    print("- meshpi-ui-macos.spec") 
    print("- meshpi-ui-linux.spec")
    print("- Dockerfile.linux")
    print("- docker-compose.build.yml")
    print("- .github/workflows/build.yml")
    
    print("\nNEXT STEPS:")
    print("1. For Linux builds on any platform:")
    print("   docker-compose -f docker-compose.build.yml up build-linux")
    
    print("\n2. For automated builds on all platforms:")
    print("   - Push to GitHub with the created workflow")
    print("   - Create a release tag: git tag v1.0.0 && git push origin v1.0.0")
    print("   - GitHub Actions will build for all platforms automatically")
    
    print("\n3. For manual builds on other platforms:")
    print("   - Copy the project to Windows/macOS")
    print("   - Run: python -m PyInstaller meshpi-ui-[platform].spec")
    
    return True

def create_run_scripts():
    """Create platform-specific run scripts"""
    platform_name = detect_platform()
    
    if platform_name == "windows":
        # Windows batch file
        with open("run.bat", "w") as f:
            f.write("@echo off\n")
            f.write("call venv\\Scripts\\activate\n")
            f.write("python main.py\n")
            f.write("pause\n")
        print("✓ Created run.bat")
        
        # Windows build script
        with open("build.bat", "w") as f:
            f.write("@echo off\n")
            f.write("echo Building Meshtastic UI executable...\n")
            f.write("call venv\\Scripts\\activate\n")
            f.write("python setup.py build\n")
            f.write("pause\n")
        print("✓ Created build.bat")
        
    else:
        # Unix shell script
        with open("run.sh", "w") as f:
            f.write("#!/bin/bash\n")
            f.write("source venv/bin/activate\n")
            f.write("python main.py\n")
        os.chmod("run.sh", 0o755)
        print("✓ Created run.sh")
        
        # Unix build script
        with open("build.sh", "w") as f:
            f.write("#!/bin/bash\n")
            f.write("echo \"Building Meshtastic UI executable...\"\n")
            f.write("source venv/bin/activate\n")
            f.write("python setup.py build\n")
        os.chmod("build.sh", 0o755)
        print("✓ Created build.sh")

def main():
    """Main setup function"""
    print("Meshtastic UI Setup")
    print("=" * 30)
    
    # Check if this is a build command
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        if not build_executable():
            sys.exit(1)
        return
    
    # Detect platform
    platform_name = detect_platform()
    print(f"Detected platform: {platform_name}")
    
    if platform_name == "unknown":
        print("Unsupported platform")
        sys.exit(1)
    
    # Check Python version
    if not check_python_version():
        print("Please install Python 3.8 or higher")
        sys.exit(1)
    
    print(f"Python version: {sys.version}")
    
    # Create virtual environment
    if not create_virtual_environment():
        print("Failed to create virtual environment")
        sys.exit(1)
    
    # Install dependencies
    try:
        if not install_dependencies():
            print("Failed to install dependencies")
            sys.exit(1)
    except Exception as e:
        print(f"Failed to install dependencies: {e}")
        sys.exit(1)
    
    # Create run scripts
    create_run_scripts()
    
    print("\n✓ Setup completed successfully!")
    print("\nTo run the application:")
    if platform_name == "windows":
        print("  run.bat")
    else:
        print("  ./run.sh")
    
    print("\nTo build executable:")
    print("  python setup.py build        # Build for current platform")
    print("  python setup.py build --all  # Setup for all platforms")
    if platform_name == "windows":
        print("  or use: build.bat")
    else:
        print("  or use: ./build.sh")

if __name__ == "__main__":
    main() 