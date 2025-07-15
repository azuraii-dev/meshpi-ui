#!/usr/bin/env python3
"""
Data Location Utility for Meshtastic UI
Shows where your databases, logs, and config files are stored
"""

import sys
import os
from pathlib import Path

try:
    from utils.paths import get_runtime_info, ensure_data_directories
except ImportError:
    print("Error: utils.paths module not found. Please run from the project directory.")
    sys.exit(1)

def main():
    print("=" * 60)
    print("MESHTASTIC UI - DATA LOCATION INFO")
    print("=" * 60)
    
    # Get runtime information
    runtime_info = get_runtime_info()
    
    # Ensure directories exist and get current paths
    paths = ensure_data_directories()
    
    print(f"Running Mode: {'Executable' if runtime_info['is_executable'] else 'Development'}")
    print(f"Platform: {runtime_info['platform']}")
    
    if runtime_info['is_executable']:
        print(f"Executable Location: {runtime_info['executable_dir']}")
    
    print("\nDATA STORAGE LOCATIONS:")
    print("-" * 30)
    
    print(f"📁 Data Directory: {paths['data']}")
    print(f"   └── Contains: Database, exported files")
    
    print(f"📄 Database File: {paths['database']}")
    db_exists = os.path.exists(paths['database'])
    if db_exists:
        db_size = os.path.getsize(paths['database']) / 1024  # KB
        print(f"   └── Status: Exists ({db_size:.1f} KB)")
    else:
        print(f"   └── Status: Not created yet")
    
    print(f"📋 Logs Directory: {paths['logs']}")
    
    print(f"⚙️  Config Directory: {paths['config']}")
    
    # Show directory contents if they exist
    if os.path.exists(paths['data']):
        print(f"\nFILES IN DATA DIRECTORY:")
        print("-" * 30)
        try:
            files = list(Path(paths['data']).iterdir())
            if files:
                for file_path in sorted(files):
                    if file_path.is_file():
                        size_kb = file_path.stat().st_size / 1024
                        print(f"  📄 {file_path.name} ({size_kb:.1f} KB)")
                    elif file_path.is_dir():
                        print(f"  📁 {file_path.name}/")
            else:
                print("  (No files yet - run the app to create data)")
        except PermissionError:
            print("  (Permission denied - cannot list contents)")
    
    print(f"\nPLATFORM-SPECIFIC PATHS:")
    print("-" * 30)
    if runtime_info['platform'] == 'Windows':
        print("  Windows: Data stored in %APPDATA%\\MeshtasticUI")
        print("  Example: C:\\Users\\YourName\\AppData\\Roaming\\MeshtasticUI")
    elif runtime_info['platform'] == 'Darwin':
        print("  macOS: Data in ~/Library/Application Support/MeshtasticUI")
        print("  Config in ~/Library/Preferences/MeshtasticUI")
    else:
        print("  Linux: Data in ~/.local/share/MeshtasticUI")
        print("  Config in ~/.config/MeshtasticUI")
    
    print(f"\nTO ACCESS YOUR DATA:")
    print("-" * 30)
    if runtime_info['platform'] == 'Windows':
        print("  1. Press Win+R, type: %APPDATA%\\MeshtasticUI")
        print("  2. Or navigate to the path shown above")
    elif runtime_info['platform'] == 'Darwin':
        print("  1. In Finder: Go → Go to Folder → ~/Library/Application Support/MeshtasticUI")
        print("  2. Or use Terminal: open ~/Library/Application\\ Support/MeshtasticUI")
    else:
        print("  1. File manager: ~/.local/share/MeshtasticUI")
        print("  2. Terminal: cd ~/.local/share/MeshtasticUI")
    
    print(f"\nBACKUP YOUR DATA:")
    print("-" * 30)
    print(f"  Copy this entire folder: {paths['data']}")
    print(f"  Important files: meshpy_data.db (your message/node history)")
    
    print("=" * 60)

if __name__ == "__main__":
    main() 