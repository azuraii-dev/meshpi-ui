# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Get platform-specific settings
block_cipher = None
platform = sys.platform

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
    # ('data_folder', 'data_folder'),  # Example
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
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove duplicate entries
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Platform-specific executable settings
if platform.startswith('win'):
    exe_name = 'MeshtasticUI.exe'
    console = False  # Hide console window
    icon = os.path.abspath('assets/icon.ico')  # Use absolute path
elif platform.startswith('darwin'):
    exe_name = 'MeshtasticUI'
    console = False
    icon = os.path.abspath('assets/icon.icns')  # Use absolute path
else:  # Linux
    exe_name = 'MeshtasticUI'
    console = False
    icon = os.path.abspath('assets/icon.png')  # Use absolute path

# Check if icon exists, otherwise don't use it
if not os.path.exists(icon):
    icon = None
    print(f"[ERROR] Warning: Icon file not found: {icon}")
else:
    icon_size = os.path.getsize(icon)
    print(f"[OK] Using icon: {icon} (size: {icon_size} bytes)")
    if icon_size < 5000:
        print(f"[WARNING] Icon file seems small ({icon_size} bytes) - may be low quality")
    
    # Also try to validate it's a proper ICO file
    if icon.endswith('.ico'):
        try:
            with open(icon, 'rb') as f:
                header = f.read(6)
                if header[:4] != b'\x00\x00\x01\x00':
                    print(f"[WARNING] {icon} doesn't appear to be a valid ICO file")
                else:
                    icon_count = int.from_bytes(header[4:6], 'little')
                    print(f"[OK] ICO file contains {icon_count} icon sizes")
        except Exception as e:
            print(f"[WARNING] Could not validate ICO file: {e}")

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=exe_name,
    debug=True,  # Enable debug mode for troubleshooting
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress executable
    upx_exclude=[],
    runtime_tmpdir=None,
    console=console,
    disable_windowed_traceback=False,
    argv_emulation=False,  # Critical: Keep this False for macOS
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
    version='version_info.txt' if os.path.exists('version_info.txt') else None,
    uac_admin=False,  # Don't require admin
    uac_uiaccess=False,  # Don't require UI access
)

# macOS specific: Create .app bundle
if platform.startswith('darwin'):
    app = BUNDLE(
        exe,
        name='MeshtasticUI.app',
        icon=icon,
        bundle_identifier='com.meshpi.ui',
        info_plist={
            'CFBundleName': 'Meshtastic UI',
            'CFBundleDisplayName': 'Meshtastic UI',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
            'NSHumanReadableCopyright': 'Copyright © 2024',
            'LSMinimumSystemVersion': '10.9.0',
            'NSRequiresAquaSystemAppearance': False,  # Support dark mode
            'LSApplicationCategoryType': 'public.app-category.utilities',
            'NSPrincipalClass': 'NSApplication',  # Ensure proper app initialization
            'NSMainNibFile': '',  # Prevent NIB file loading issues
            'LSUIElement': False,  # Explicitly show in dock (opposite of background app)
        },
    ) 