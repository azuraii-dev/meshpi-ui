# Building Meshtastic UI Executables

This document explains how to build standalone executables for different platforms using the integrated build system.

## Quick Start

### First Time Setup
```bash
# Setup development environment (creates venv, installs dependencies)
python setup.py
```

### Building Executables

#### Single Platform Build
```bash
# Build executable for current platform only
python setup.py build
```

#### Multi-Platform Build Setup
```bash
# Setup for building on all platforms
python setup.py build --all
```

Or use the convenience scripts:
- **Windows**: `build.bat`
- **macOS/Linux**: `./build.sh`

## What Gets Built

### Windows
- **Output**: `dist/MeshtasticUI.exe`
- **Type**: Single executable file
- **Size**: ~50-80MB (depending on dependencies)

### macOS  
- **Output**: `dist/MeshtasticUI.app`
- **Type**: Application bundle
- **Size**: ~60-90MB
- **Note**: Supports both Intel and Apple Silicon

### Linux
- **Output**: `dist/MeshtasticUI`
- **Type**: Executable binary
- **Size**: ~50-80MB

## Dependencies Handled Automatically

The build system automatically includes:
- ✅ **Meshtastic library** (including native components)
- ✅ **Optional dependencies** (matplotlib, tkintermapview)
- ✅ **Serial port libraries** (pyserial)
- ✅ **GUI libraries** (tkinter)
- ✅ **Database support** (sqlite3)
- ✅ **Network libraries** (requests)

## Build Process

1. **Checks virtual environment** - Creates if missing
2. **Installs PyInstaller** - If not already present
3. **Cleans previous builds** - Removes old `dist/` and `build/` folders
4. **Analyzes dependencies** - Using `meshpi-ui.spec` configuration
5. **Builds executable** - Packages everything into standalone app
6. **Reports results** - Shows file location and size

## Customization

### Icon Files
Place platform-specific icons in the root directory:
- `icon.ico` - Windows icon
- `icon.icns` - macOS icon  
- `icon.png` - Linux icon

### Build Configuration
Edit `meshpi-ui.spec` to customize:
- Hidden imports
- Excluded modules (for smaller file size)
- Data files to include
- Platform-specific settings

## Troubleshooting

### Missing Dependencies
If build fails with "No module named X":
```bash
# Install missing module in virtual environment
venv/Scripts/pip install MODULE_NAME  # Windows
venv/bin/pip install MODULE_NAME      # macOS/Linux
```

### Large File Size
To reduce executable size, edit `meshpi-ui.spec` and add to `excludes`:
```python
excludes = [
    'matplotlib',  # If you don't need charts
    'numpy',       # If not using analytics
    # ... other unused modules
]
```

### Permission Issues (Windows)
Run Command Prompt as Administrator if you get permission errors.

### macOS Code Signing
For distribution on macOS:
```bash
# Sign the application (requires Apple Developer account)
codesign --force --deep --sign "Developer ID Application: Your Name" dist/MeshtasticUI.app
```

## Development Workflow

During development, you can quickly rebuild after code changes:

```bash
# Make your code changes...
git add .
git commit -m "Updated feature X"

# Rebuild executable
python setup.py build

# Test the executable
./dist/MeshtasticUI  # Linux/macOS
dist\MeshtasticUI.exe  # Windows
```

## Distribution

### Windows
- Share the `.exe` file directly
- Or create an installer using NSIS/Inno Setup

### macOS
- Share the `.app` bundle
- Or create a `.dmg` disk image
- Consider notarization for App Store distribution

### Linux
- Share the binary directly
- Or package as AppImage/Flatpak/Snap
- Or create distribution-specific packages (.deb, .rpm)

## File Sizes (Approximate)

| Platform | Minimal Build | Full Build (with matplotlib) |
|----------|---------------|-------------------------------|
| Windows  | ~40MB         | ~70MB                        |
| macOS    | ~50MB         | ~80MB                        |
| Linux    | ~35MB         | ~65MB                        |

*Sizes may vary based on Python version and installed dependencies*

## Data Storage in Executables

When running as an executable, your data is stored in OS-appropriate user directories:

### Windows
- **Data Location**: `%APPDATA%\MeshtasticUI`
- **Example**: `C:\Users\YourName\AppData\Roaming\MeshtasticUI`
- **Access**: Press `Win+R`, type `%APPDATA%\MeshtasticUI`

### macOS
- **Data Location**: `~/Library/Application Support/MeshtasticUI`
- **Config Location**: `~/Library/Preferences/MeshtasticUI`
- **Access**: Finder → Go → Go to Folder → `~/Library/Application Support/MeshtasticUI`

### Linux
- **Data Location**: `~/.local/share/MeshtasticUI`
- **Config Location**: `~/.config/MeshtasticUI`
- **Access**: File manager or `cd ~/.local/share/MeshtasticUI`

### What's Stored
- **Database**: `meshpi_data.db` (messages, nodes, analytics)
- **Logs**: Application logs and error reports
- **Config**: User preferences and settings
- **Exports**: Any exported data files

### Finding Your Data
Run this utility to see exactly where your data is stored:
```bash
python scripts/show_data_location.py
```

### Backup Your Data
To backup your Meshtastic UI data:
1. Locate your data directory (see above)
2. Copy the entire `MeshtasticUI` folder
3. The database file `meshpi_data.db` contains all your important data

### Development vs Executable
- **Development**: Data stored in local `database/` folder
- **Executable**: Data stored in user directories (persistent across updates)

## Multi-Platform Building

The `--all` flag creates a complete setup for building on all platforms:

### What It Creates
```bash
python setup.py build --all
```

**Generated Files:**
- `meshpi-ui-windows.spec` - Windows build configuration
- `meshpi-ui-macos.spec` - macOS build configuration  
- `meshpi-ui-linux.spec` - Linux build configuration
- `Dockerfile.linux` - Docker configuration for Linux builds
- `docker-compose.build.yml` - Easy Docker commands
- `.github/workflows/build.yml` - GitHub Actions for automated builds

### Cross-Platform Build Options

#### Option 1: Docker (Linux builds anywhere)
```bash
# Build Linux executable on any platform
docker-compose -f docker-compose.build.yml up build-linux
# Output: ./dist-linux/MeshtasticUI
```

#### Option 2: GitHub Actions (Automated)
1. Push your code to GitHub
2. Create a release tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
3. GitHub automatically builds for all platforms
4. Download from GitHub Releases

#### Option 3: Manual (Copy to each platform)
1. Copy project to Windows/macOS/Linux machine
2. Run platform-specific build:
   ```bash
   python -m PyInstaller meshpi-ui-windows.spec  # On Windows
   python -m PyInstaller meshpi-ui-macos.spec    # On macOS  
   python -m PyInstaller meshpi-ui-linux.spec    # On Linux
   ```

### Build Matrix

| Build Method | Windows | macOS | Linux | Automation |
|--------------|---------|-------|-------|------------|
| Native       | ✅      | ✅    | ✅    | Manual     |
| Docker       | ❌      | ❌    | ✅    | Semi-auto  |
| GitHub Actions | ✅    | ✅    | ✅    | Full-auto  |

**Recommended:** Use GitHub Actions for releases, Docker for Linux testing. 