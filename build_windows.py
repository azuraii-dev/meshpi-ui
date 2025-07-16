#!/usr/bin/env python3
"""
Windows-specific build script for Meshtastic UI
Handles icon embedding issues and Windows-specific PyInstaller problems
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_windows_requirements():
    """Check Windows-specific build requirements"""
    issues = []
    
    # Check if on Windows
    if sys.platform != 'win32':
        print("⚠️  This script is designed for Windows builds")
        print("   Current platform:", sys.platform)
    
    # Check for PyInstaller
    try:
        import PyInstaller
        print(f"✅ PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        issues.append("PyInstaller not installed")
    
    # Check icon file
    if not os.path.exists('icon.ico'):
        issues.append("icon.ico not found")
    else:
        icon_size = os.path.getsize('icon.ico')
        print(f"✅ Icon file: icon.ico ({icon_size} bytes)")
        if icon_size < 5000:
            issues.append("Icon file seems too small (may be low quality)")
    
    # Check spec file
    if not os.path.exists('meshpi-ui.spec'):
        issues.append("meshpi-ui.spec not found")
    else:
        print("✅ Spec file found")
    
    return issues

def clean_build():
    """Clean previous build artifacts"""
    print("🧹 Cleaning previous builds...")
    
    dirs_to_remove = ['build', 'dist']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"  ✅ Removed {dir_name}/")
            except PermissionError:
                print(f"  ❌ Could not remove {dir_name}/ - files may be in use")
                print("     Please close any running MeshtasticUI.exe and try again")
                return False
            except Exception as e:
                print(f"  ⚠️  Warning: {e}")
    
    return True

def build_executable():
    """Build the executable with Windows-specific optimizations"""
    print("🔨 Building Windows executable...")
    
    # Method 1: Try with spec file
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',              # Clean cache
        '--noconfirm',          # Overwrite output directory
        'meshpi-ui.spec'
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0:
            print("✅ Build completed successfully!")
            return check_build_output()
        else:
            print("❌ Build failed with spec file")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            
            # Try alternative method
            return build_executable_alternative()
            
    except Exception as e:
        print(f"❌ Build error: {e}")
        return build_executable_alternative()

def build_executable_alternative():
    """Alternative build method with explicit icon parameter"""
    print("🔄 Trying alternative build method...")
    
    # Method 2: Direct command with explicit icon
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        '--onefile',            # Single file executable
        '--windowed',           # No console window
        '--icon=icon.ico',      # Explicit icon path
        '--name=MeshtasticUI',  # Explicit name
        '--add-data=database;database',  # Include database folder
        'main.py'
    ]
    
    print(f"Running alternative: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0:
            print("✅ Alternative build completed!")
            return check_build_output()
        else:
            print("❌ Alternative build also failed")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Alternative build error: {e}")
        return False

def check_build_output():
    """Check the build output and verify icon embedding"""
    exe_path = "dist/MeshtasticUI.exe"
    
    if not os.path.exists(exe_path):
        print(f"❌ Executable not found: {exe_path}")
        return False
    
    exe_size = os.path.getsize(exe_path)
    print(f"✅ Executable created: {exe_path}")
    print(f"   Size: {exe_size / (1024*1024):.1f} MB")
    
    # Try to verify icon embedding (basic check)
    try:
        with open(exe_path, 'rb') as f:
            content = f.read(1024 * 1024)  # Read first 1MB
            if b'icon.ico' in content or b'ICON' in content:
                print("✅ Icon appears to be embedded")
            else:
                print("⚠️  Warning: Icon may not be properly embedded")
    except Exception as e:
        print(f"⚠️  Could not verify icon embedding: {e}")
    
    return True

def clear_windows_icon_cache():
    """Clear Windows icon cache to force refresh"""
    print("🔄 Clearing Windows icon cache...")
    
    cache_commands = [
        'ie4uinit.exe -ClearIconCache',
        'ie4uinit.exe -show',
        'taskkill /IM explorer.exe /F && start explorer.exe'
    ]
    
    for cmd in cache_commands:
        try:
            print(f"   Running: {cmd}")
            if 'taskkill' in cmd:
                # This restarts Explorer, ask user first
                response = input("   Restart Windows Explorer to refresh icons? (y/n): ")
                if response.lower() != 'y':
                    continue
            
            subprocess.run(cmd, shell=True, capture_output=True)
            
        except Exception as e:
            print(f"   ⚠️  Command failed: {e}")

def main():
    """Main build function"""
    print("🪟 Meshtastic UI - Windows Build Script")
    print("=" * 45)
    
    # Check requirements
    issues = check_windows_requirements()
    if issues:
        print("\n❌ Build requirements not met:")
        for issue in issues:
            print(f"   • {issue}")
        print("\nPlease fix these issues and try again.")
        return False
    
    print("\n✅ All requirements met!")
    
    # Clean previous builds
    if not clean_build():
        return False
    
    # Build executable
    if not build_executable():
        return False
    
    print("\n🎉 Build completed successfully!")
    print("\n📝 Windows-specific notes:")
    print("   • The icon should now appear in Windows Explorer")
    print("   • If icon doesn't show, try clearing icon cache")
    print("   • Test the executable by double-clicking it")
    
    # Offer to clear icon cache
    if sys.platform == 'win32':
        response = input("\nClear Windows icon cache to refresh icons? (y/n): ")
        if response.lower() == 'y':
            clear_windows_icon_cache()
    
    print(f"\n✅ Executable ready: dist/MeshtasticUI.exe")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 